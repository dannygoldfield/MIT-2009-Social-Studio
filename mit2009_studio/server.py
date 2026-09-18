from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import argparse
import json
import mimetypes
import os
import re
import shutil
import threading
import uuid
from PIL import ImageOps
from . import render
from .media import DATA, digest, ffmpeg, image_rgb, inspect, run

WEB = Path(__file__).parent / "web"
LOCK = threading.RLock()
EXECUTOR = ThreadPoolExecutor(max_workers=1)
JOBS = {}
MAX_UPLOAD = 1024 * 1024 * 1024
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".mp4", ".mov", ".m4v", ".webm", ".wav", ".mp3", ".m4a", ".aac", ".aif", ".aiff", ".flac", ".ogg"}

def initialize():
    for child in ("inputs", "exports", "jobs"):
        (DATA / child).mkdir(parents=True, exist_ok=True)
    if not (DATA / "library.json").exists():
        save_library([])
    for path in (DATA / "jobs").glob("*.json"):
        job = json.loads(path.read_text())
        if job["status"] in {"queued", "rendering"}:
            job.update(status="error", message="The studio was closed before this export finished. Make a new export to try again.")
            path.write_text(json.dumps(job, indent=2))
        JOBS[job["id"]] = job

def save_library(rows):
    with LOCK:
        tmp = DATA / "library.tmp"
        tmp.write_text(json.dumps(rows, indent=2))
        tmp.replace(DATA / "library.json")

def library():
    with LOCK:
        return json.loads((DATA / "library.json").read_text())

def add_entry(row):
    with LOCK:
        rows = library()
        rows.append(row)
        save_library(rows)

def lookup(identity):
    if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{32}", identity):
        raise ValueError("Choose a file from this studio's media library.")
    entry = next((row for row in library() if row["id"] == identity), None)
    if not entry:
        raise ValueError("That file is no longer in this media library.")
    path = (DATA / entry["file"]).resolve()
    if not path.is_relative_to(DATA.resolve()) or not path.is_file():
        raise ValueError("The selected file is unavailable in this studio.")
    return {**entry, "path": path}

def public_entry(entry):
    result = {k: v for k, v in entry.items() if k not in {"file", "path", "thumbnail", "preview", "sha256"}}
    result["url"] = f"/media/{entry['id']}"
    result["thumbnail_url"] = f"/media/{entry['id']}?thumbnail=1" if entry.get("thumbnail") else None
    result["preview_url"] = f"/media/{entry['id']}?preview=1" if entry.get("preview") else result["url"]
    return result

def thumbnail(path, kind, identity):
    target = DATA / "inputs" / f"{identity}-thumb.jpg"
    if kind == "image":
        image = image_rgb(path)
        image.thumbnail((360, 360))
        image.save(target, quality=80)
    elif kind == "video":
        run([ffmpeg(), "-v", "error", "-y", "-i", str(path), "-frames:v", "1", "-vf", "scale=360:360:force_original_aspect_ratio=decrease", str(target)], 60)
    return str(target.relative_to(DATA)) if target.exists() else None

def update_job(job, **changes):
    with LOCK:
        job.update(changes)
        (DATA / "jobs" / f"{job['id']}.json").write_text(json.dumps(job, indent=2))

def perform(job):
    folder = DATA / "exports" / job["id"]
    folder.mkdir()
    try:
        update_job(job, status="rendering", message="Preparing your media")
        target, role = render.RENDERERS[job["tool"]](job["config"], lookup, folder, lambda message: update_job(job, message=message))
        info = inspect(target)
        identity = uuid.uuid4().hex
        row = {"id": identity, "name": job["name"] + target.suffix, "file": str(target.relative_to(DATA)),
               "sha256": digest(target), "created": job["created"], "role": role, "review": "draft", **info}
        row["thumbnail"] = thumbnail(target, info["kind"], identity)
        preview = folder / "overlay-preview.mp4"
        if preview.exists():
            row["preview"] = str(preview.relative_to(DATA))
        add_entry(row)
        (folder / "recipe.json").write_text(json.dumps({"tool": job["tool"], "settings": job["config"], "output_sha256": row["sha256"], "review": "draft", "version": "0.2.0", "edition": "MIT 2.009 2026 Connect", "typeface": "Outfit Bold" if job["tool"] == "text" else None}, indent=2))
        update_job(job, status="done", message="Ready to review and download", result=public_entry(row))
    except Exception as error:
        update_job(job, status="error", message=str(error))

def audio_item_changes(payload):
    changes = {}
    if "audio_bucket" in payload:
        if payload["audio_bucket"] not in {"bed", "effect", "wildcard"}:
            raise ValueError("Choose Sound beds, Sound Effects, or Wildcards.")
        changes["audio_bucket"] = payload["audio_bucket"]
    if "assessment" in payload:
        if payload["assessment"] not in {"unreviewed", "keep", "maybe", "pass"}:
            raise ValueError("Choose Keep, Maybe, Pass, or Not assessed.")
        changes["assessment"] = payload["assessment"]
    if "notes" in payload:
        if not isinstance(payload["notes"], str) or len(payload["notes"]) > 500:
            raise ValueError("Keep your note under 500 characters.")
        changes["notes"] = payload["notes"]
    return changes

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, payload, status=200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def local_request(self, mutation=False):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            raise ValueError("Open this studio using its localhost address.")
        if mutation:
            origin = self.headers.get("Origin")
            if origin and origin not in {"http://" + host for host in allowed}:
                raise ValueError("This request did not come from the studio.")
            if self.headers.get("X-Studio-Request") != "1":
                raise ValueError("Refresh the studio and try again.")

    def serve_file(self, path, download=None):
        length = path.stat().st_size
        start, end = 0, length-1
        requested = self.headers.get("Range")
        if requested:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", requested)
            if not match or (not match[1] and not match[2]):
                return self.respond({"error": "Invalid range"}, 416)
            if not match[1]:
                start = max(0, length-int(match[2]))
            else:
                start = int(match[1])
                end = min(end, int(match[2])) if match[2] else end
            if start > end or start >= length:
                return self.respond({"error": "Range unavailable"}, 416)
        self.send_response(206 if requested else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end-start+1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        if requested:
            self.send_header("Content-Range", f"bytes {start}-{end}/{length}")
        if download:
            clean = re.sub(r"[^A-Za-z0-9._ -]", "_", download)
            self.send_header("Content-Disposition", f'attachment; filename="{clean}"')
        self.end_headers()
        with path.open("rb") as source:
            source.seek(start)
            remaining = end-start+1
            while remaining:
                chunk = source.read(min(1024*1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self):
        try:
            self.local_request()
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/api/library":
                return self.respond({"items": [public_entry(row) for row in library()]})
            if path == "/api/jobs":
                with LOCK:
                    return self.respond({"jobs": sorted(JOBS.values(), key=lambda j: j["created"], reverse=True)[:50]})
            if path.startswith("/media/"):
                row = lookup(path.removeprefix("/media/"))
                file = row["path"]
                if query.get("thumbnail") and row.get("thumbnail"):
                    file = (DATA / row["thumbnail"]).resolve()
                elif query.get("preview") and row.get("preview"):
                    file = (DATA / row["preview"]).resolve()
                if not file.is_relative_to(DATA.resolve()):
                    raise ValueError("Invalid media path.")
                return self.serve_file(file, row["name"] if query.get("download") else None)
            if path.startswith("/brand-2026/"):
                asset = (WEB / unquote(path.lstrip("/"))).resolve()
                if asset.is_relative_to((WEB / "brand-2026").resolve()) and asset.is_file():
                    return self.serve_file(asset)
                return self.respond({"error": "Not found"}, 404)
            static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
            if path in static:
                return self.serve_file(WEB / static[path])
            return self.respond({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.respond({"error": str(error)}, 400)

    def do_POST(self):
        temporary = None
        try:
            self.local_request(mutation=True)
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_UPLOAD:
                raise ValueError("Choose a file smaller than 1 GB.")
            if parsed.path == "/api/import":
                name = Path(parse_qs(parsed.query).get("name", ["file"])[0]).name
                suffix = Path(name).suffix.lower()
                if suffix not in EXTENSIONS:
                    raise ValueError("Choose a JPG, PNG, TIFF, video, or audio file.")
                identity = uuid.uuid4().hex
                temporary = DATA / "inputs" / f"{identity}{suffix}"
                remaining = length
                with temporary.open("wb") as output:
                    while remaining:
                        block = self.rfile.read(min(1024*1024, remaining))
                        if not block:
                            raise ValueError("The upload was interrupted.")
                        output.write(block)
                        remaining -= len(block)
                info = inspect(temporary)
                row = {"id": identity, "name": name, "file": str(temporary.relative_to(DATA)), "sha256": digest(temporary),
                       "created": datetime.now(timezone.utc).isoformat(), "role": "source", **info}
                row["thumbnail"] = thumbnail(temporary, info["kind"], identity)
                if info["kind"] == "audio":
                    bucket = parse_qs(parsed.query).get("audio_bucket", ["wildcard"])[0]
                    row["audio_bucket"] = bucket if bucket in {"bed", "effect", "wildcard"} else "wildcard"
                    row["assessment"] = "unreviewed"
                add_entry(row)
                temporary = None
                return self.respond(public_entry(row), 201)
            if length > 1024*1024:
                raise ValueError("The request is too large.")
            payload = json.loads(self.rfile.read(length))
            if parsed.path == "/api/render":
                tool = payload.get("tool")
                if tool not in render.RENDERERS or not isinstance(payload.get("config"), dict):
                    raise ValueError("Choose one of the four studio tools.")
                job = {"id": uuid.uuid4().hex, "tool": tool, "config": payload["config"],
                       "name": str(payload.get("name") or {"audio":"2.009 Soundtrack", "video":"2.009 Photo Edit", "text":"2.009 Animated Text", "assemble":"2.009 Social Post"}[tool])[:120],
                       "created": datetime.now(timezone.utc).isoformat(), "status": "queued", "message": "Waiting to render"}
                update_job(job)
                with LOCK:
                    JOBS[job["id"]] = job
                EXECUTOR.submit(perform, job)
                return self.respond(job, 202)
            if parsed.path == "/api/audio-item":
                identity = payload.get("id")
                entry = lookup(identity)
                if entry["kind"] != "audio":
                    raise ValueError("Choose an audio file.")
                changes = audio_item_changes(payload)
                with LOCK:
                    rows = library()
                    for row in rows:
                        if row["id"] == identity:
                            row.update(changes)
                    save_library(rows)
                return self.respond({"ok": True})
            if parsed.path == "/api/review":
                identity = payload.get("id")
                lookup(identity)
                if payload.get("review") not in {"draft", "keep", "approved"}:
                    raise ValueError("Choose a valid review status.")
                with LOCK:
                    rows = library()
                    for row in rows:
                        if row["id"] == identity:
                            row["review"] = payload["review"]
                    save_library(rows)
                return self.respond({"ok": True})
            return self.respond({"error": "Not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            self.respond({"error": str(error)}, 400)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description="Open the private, local MIT 2.009 Test Studio.")
    parser.add_argument("--port", type=int, default=8772)
    args = parser.parse_args()
    initialize()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"MIT 2.009 Test Studio: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
