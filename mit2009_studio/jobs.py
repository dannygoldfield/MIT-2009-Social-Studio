"""One durable local queue and one worker. Completed candidates survive retries."""

import fcntl
import json
import threading
import time

from . import media
from .render import RENDERERS
from .service import VERSION
from .store import now, packed, unpack


class Worker:
    def __init__(self, studio, size_override=None):
        self.studio = studio
        self.store = studio.store
        self.size_override = size_override  # Tests only; never exposed by the API.
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = None

    def start(self):
        self.lock = self.store.path("worker.lock").open("a+")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.lock.close()
            raise RuntimeError(
                "This data folder is already open in another studio. Use one server process."
            ) from error
        with self.store.connect() as db:
            db.execute(
                "UPDATE jobs SET status='failed',error='Interrupted when the studio stopped. Retry to finish missing candidates.',finished_at=? WHERE status='running'",
                (now(),),
            )
            db.execute(
                "UPDATE candidates SET status='failed',error='Interrupted. Retry the batch.' WHERE status='running'"
            )
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.loop, name="studio-render-worker", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=310)
        if self.lock:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()

    def progress(self, job_id, message):
        if self.stop_event.is_set():
            raise RuntimeError("Studio stopped. Retry this batch to finish the remaining candidates.")
        with self.store.connect() as db:
            db.execute("UPDATE jobs SET progress=? WHERE id=?", (message, job_id))

    def claim(self):
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            job = unpack(row)
            db.execute(
                "UPDATE jobs SET status='running',started_at=?,progress='Preparing the batch' WHERE id=?",
                (now(), job["id"]),
            )
            return job

    def loop(self):
        while not self.stop_event.is_set():
            job = self.claim()
            if job:
                self.perform(job)
            else:
                self.stop_event.wait(0.4)

    def perform(self, job):
        start = time.monotonic()
        errors = []
        rows = self.store.all(
            "SELECT * FROM candidates WHERE batch_id=? AND status!='ready' ORDER BY slot", (job["batch_id"],)
        )
        for c in rows:
            if self.stop_event.is_set():
                errors.append("Studio stopped before the batch finished.")
                break
            try:
                with self.store.connect() as db:
                    db.execute("UPDATE candidates SET status='running',error=NULL WHERE id=?", (c["id"],))
                folder = self.store.path(f"renders/{job['id']}/{c['id']}")
                folder.mkdir(parents=True, exist_ok=False)
                sources = []
                for identity in c["sources"]:
                    a = self.store.one("SELECT * FROM assets WHERE id=?", (identity,))
                    a["file"] = self.store.path(a["path"])
                    if media.digest(a["file"]) != a["normalized_sha256"]:
                        raise ValueError("A source file changed. Upload it again before generating.")
                    sources.append(a)
                context = {}
                for stage, identity in c["context"].items():
                    earlier = self.studio.candidate(identity)
                    artifact = earlier["artifacts"]["output"]
                    earlier["file"] = self.store.path(artifact["path"])
                    if media.digest(earlier["file"]) != artifact["sha256"]:
                        raise ValueError(
                            "An earlier candidate file changed. Regenerate it before continuing."
                        )
                    context[stage] = earlier
                settings = c["settings"]
                size = self.size_override or media.SIZES[settings["aspect"]]
                candidate_start = time.monotonic()
                paths, analysis = RENDERERS[c["stage"]](
                    settings,
                    sources,
                    context,
                    folder,
                    size,
                    lambda message, name=settings["style"]["name"]: self.progress(
                        job["id"], f"{name}: {message}"
                    ),
                )
                technical = media.verify_output(
                    paths["output"],
                    settings["duration"],
                    size if c["stage"] != "audio" else None,
                    alpha=c["stage"] == "text",
                    audio=c["stage"] in ("audio", "assembly"),
                )
                if paths["preview"] != paths["output"]:
                    media.verify_output(paths["preview"], settings["duration"], size)
                analysis.update(
                    technical=technical, elapsed_seconds=round(time.monotonic() - candidate_start, 3)
                )
                artifacts = {
                    key: {
                        "path": self.store.relative(path),
                        "sha256": media.digest(path),
                        "bytes": path.stat().st_size,
                    }
                    for key, path in paths.items()
                }
                if c["stage"] != "audio":
                    poster = folder / "poster.jpg"
                    media.ff(
                        ["-ss", "3", "-i", paths["preview"], "-frames:v", 1, "-vf", "scale=480:-2", poster]
                    )
                    artifacts["poster"] = {
                        "path": self.store.relative(poster),
                        "sha256": media.digest(poster),
                        "bytes": poster.stat().st_size,
                    }
                manifest = {
                    "candidate_id": c["id"],
                    "job_id": job["id"],
                    "attempt": job["attempt"],
                    "app_version": VERSION,
                    "settings": settings,
                    "context": c["context"],
                    "sources": c["sources"],
                    "analysis": analysis,
                    "artifacts": artifacts,
                }
                (folder / "recipe.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
                with self.store.connect() as db:
                    db.execute(
                        "UPDATE candidates SET status='ready',analysis=?,artifacts=?,error=NULL WHERE id=?",
                        (packed(analysis), packed(artifacts), c["id"]),
                    )
            except Exception as error:
                message = str(error)[:2000]
                errors.append(f"{c['settings']['style']['name']}: {message}")
                with self.store.connect() as db:
                    db.execute("UPDATE candidates SET status='failed',error=? WHERE id=?", (message, c["id"]))
        with self.store.connect() as db:
            db.execute(
                "UPDATE jobs SET status=?,finished_at=?,elapsed_seconds=?,progress=?,error=? WHERE id=?",
                (
                    "failed" if errors else "done",
                    now(),
                    round(time.monotonic() - start, 3),
                    "Some candidates need a retry" if errors else "Ready to compare",
                    "\n".join(errors) or None,
                    job["id"],
                ),
            )
