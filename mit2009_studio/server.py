"""Local-only HTTP boundary. Run exactly one process for each data directory."""

import argparse
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import media
from .jobs import Worker
from .models import Approval, Generate, NewProject, Rating
from .service import VERSION, Studio
from .styles import load_presets

WEB = Path(__file__).parent / "web"
ROOT = Path(__file__).resolve().parents[1]
MAX_UPLOAD = 100 * 1024 * 1024


def create_app(data_dir=None, start_worker=True, size_override=None):
    studio = Studio(data_dir or os.environ.get("STUDIO_DATA_DIR", ROOT / "data/candidate-engine"))
    worker = Worker(studio, size_override)

    @asynccontextmanager
    async def lifespan(app):
        media.executable("ffmpeg")
        media.executable("ffprobe")
        if start_worker:
            worker.start()
        yield
        if start_worker:
            worker.stop()

    app = FastAPI(title="MIT 2.009 Candidate Studio", version=VERSION, lifespan=lifespan)
    app.state.studio = studio
    app.state.worker = worker

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        host = request.url.hostname
        if host not in {"localhost", "127.0.0.1", "testserver"}:
            return JSONResponse({"error": "Open the studio using its localhost address."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if request.headers.get("x-studio-request") != "1" or (
                origin and urlparse(origin).netloc != request.headers.get("host")
            ):
                return JSONResponse({"error": "This request must come from the studio."}, status_code=403)
            try:
                if int(request.headers.get("content-length", 0)) > MAX_UPLOAD + 1024 * 1024:
                    return JSONResponse({"error": "Upload files smaller than 100 MB."}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "Invalid content length."}, status_code=400)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; frame-ancestors 'none'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=400)

    @app.get("/api/status")
    def status():
        return {
            "version": VERSION,
            "duration": 15,
            "provider": "local-dsp",
            "generation": "local transformations; no AI or paid API calls",
            "presets": load_presets(),
            "data_dir": str(studio.store.root),
        }

    @app.post("/api/demo", status_code=201)
    def demo():
        from .demo import create_demo

        return create_demo(studio)

    @app.get("/api/projects")
    def projects():
        return studio.projects()

    @app.post("/api/projects", status_code=201)
    def create_project(request: NewProject):
        return studio.create_project(request)

    @app.get("/api/projects/{project_id}")
    def project(project_id: str):
        return studio.detail(project_id)

    @app.post("/api/projects/{project_id}/assets", status_code=201)
    def upload(project_id: str, role: str = Form(...), file: UploadFile = File(...)):
        studio.project(project_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=studio.store.root, suffix=".upload", delete=False) as out:
                temporary = Path(out.name)
                total = 0
                while chunk := file.file.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_UPLOAD:
                        raise HTTPException(413, "Upload files smaller than 100 MB.")
                    out.write(chunk)
                if not total:
                    raise ValueError("Choose a non-empty file.")
            return studio.add_asset(project_id, role, file.filename or "source", temporary)
        finally:
            file.file.close()
            if temporary:
                temporary.unlink(missing_ok=True)

    @app.post("/api/projects/{project_id}/generate", status_code=202)
    def generate(project_id: str, request: Generate):
        return studio.enqueue(project_id, request)

    @app.post("/api/candidates/{candidate_id}/rating")
    def rate(candidate_id: str, request: Rating):
        return studio.rate(candidate_id, request.stars)

    @app.post("/api/candidates/{candidate_id}/select")
    def select(candidate_id: str):
        return studio.select(candidate_id)

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    def retry(job_id: str):
        return studio.retry(job_id)

    @app.post("/api/projects/{project_id}/approvals", status_code=201)
    def approve(project_id: str, request: Approval):
        return studio.approve(project_id, request)

    @app.get("/api/approvals/{approval_id}")
    def approval(approval_id: str):
        return studio.store.one("SELECT * FROM approvals WHERE id=?", (approval_id,))

    @app.post("/api/approvals/{approval_id}/export", status_code=201)
    def export(approval_id: str):
        return studio.export(approval_id)

    @app.get("/api/exports/{export_id}/file")
    def export_file(export_id: str):
        item = studio.store.one("SELECT * FROM exports WHERE id=?", (export_id,))
        path = studio.store.path(item["path"])
        if media.digest(path) != item["sha256"]:
            raise ValueError("The export changed. Create a fresh export from the approval.")
        return FileResponse(path, filename="2.009-approved-media.zip", media_type="application/zip")

    @app.get("/api/assets/{asset_id}/file")
    def asset_file(asset_id: str):
        item = studio.store.one("SELECT * FROM assets WHERE id=?", (asset_id,))
        return FileResponse(studio.store.path(item["path"]))

    @app.get("/api/candidates/{candidate_id}/file/{kind}")
    def candidate_file(candidate_id: str, kind: str):
        item = studio.candidate(candidate_id)
        if kind not in ("output", "preview", "poster") or kind not in item["artifacts"]:
            raise HTTPException(404, "That media file is not available.")
        path = studio.store.path(item["artifacts"][kind]["path"])
        if not path.is_file():
            raise HTTPException(404, "The media file is missing.")
        return FileResponse(path)

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app


def main():
    parser = argparse.ArgumentParser(description="MIT 2.009 Candidate Studio (local only)")
    parser.add_argument("--port", type=int, default=8773)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()
    uvicorn.run(create_app(args.data_dir), host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
