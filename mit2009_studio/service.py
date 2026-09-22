"""Candidate rules and transactional decisions, independent of rendering or HTTP."""

import secrets
import shutil
import zipfile
from pathlib import Path

from . import media
from .analysis import audio_features, image_features
from .store import Store, now, packed, uid, unpack
from .styles import choose_styles

STAGES = ("audio", "video", "text", "assembly")
VERSION = "0.2.0"
CANDIDATES = """SELECT c.*, (SELECT stars FROM ratings r WHERE r.candidate_id=c.id ORDER BY r.id DESC LIMIT 1)
AS rating FROM candidates c"""


class Studio:
    def __init__(self, root):
        self.store = Store(root)

    def project(self, project_id):
        return self.store.one(
            "SELECT p.*,u.name AS author FROM projects p JOIN users u ON p.user_id=u.id WHERE p.id=?",
            (project_id,),
        )

    def candidate(self, candidate_id):
        return self.store.one(CANDIDATES + " WHERE c.id=?", (candidate_id,))

    def create_project(self, request):
        project_id, user_id, timestamp = uid(), uid(), now()
        with self.store.connect() as db:
            db.execute("INSERT INTO users VALUES(?,?,?)", (user_id, request.author, timestamp))
            db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?,?)",
                (project_id, request.name, user_id, request.aspect, 15, timestamp),
            )
            Store.event(db, project_id, user_id, "project_created", request.model_dump())
        return self.project(project_id)

    def projects(self):
        return self.store.all(
            "SELECT p.*,u.name AS author FROM projects p JOIN users u ON p.user_id=u.id ORDER BY p.created_at DESC"
        )

    def selections(self, project_id):
        return {
            r["stage"]: r["candidate_id"]
            for r in self.store.all("SELECT * FROM selections WHERE project_id=?", (project_id,))
        }

    @staticmethod
    def compatible(candidate, selected):
        return all(selected.get(stage) == identity for stage, identity in candidate["context"].items())

    def detail(self, project_id):
        project = self.project(project_id)
        selected = self.selections(project_id)
        candidates = self.store.all(
            CANDIDATES + " WHERE c.project_id=? ORDER BY c.created_at,c.slot", (project_id,)
        )
        for c in candidates:
            c["stale"] = not self.compatible(c, selected)
        return {
            "project": project,
            "selections": selected,
            "candidates": candidates,
            "assets": self.store.all(
                "SELECT * FROM assets WHERE project_id=? ORDER BY created_at", (project_id,)
            ),
            "batches": self.store.all(
                "SELECT * FROM batches WHERE project_id=? ORDER BY created_at", (project_id,)
            ),
            "jobs": self.store.all(
                "SELECT j.* FROM jobs j JOIN batches b ON j.batch_id=b.id WHERE b.project_id=? ORDER BY j.created_at",
                (project_id,),
            ),
            "approvals": self.store.all(
                "SELECT id,project_id,candidate_id,user_id,explanation,created_at FROM approvals WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            ),
        }

    def add_asset(self, project_id, role, name, temporary):
        project = self.project(project_id)
        if role not in ("reference", "bed", "effect", "photo"):
            raise ValueError("Choose audio reference, bed, sound effect, or photo.")
        identity = uid()
        folder = self.store.path(f"assets/{identity}")
        folder.mkdir(parents=True)
        safe_name = Path(name.replace("\\", "/")).name[:160]
        original = folder / ("original" + Path(safe_name).suffix.lower())
        shutil.copyfile(temporary, original)
        try:
            if role == "photo":
                normalized = folder / "source.jpg"
                im = media.image_rgb(original)
                info = image_features(im)
                info.update(width=im.width, height=im.height, kind="image")
                im.thumbnail((3840, 3840))
                im.save(normalized, quality=95)
            else:
                raw_info = media.probe(original)
                if not any(s["codec_type"] == "audio" for s in raw_info["streams"]):
                    raise ValueError("This file has no audio track.")
                original_duration = float(raw_info["format"].get("duration", 0))
                if original_duration <= 0 or original_duration > 600:
                    raise ValueError("Use an audio recording between a fraction of a second and ten minutes.")
                normalized = folder / "source.wav"
                samples = media.read_audio(original, project["duration"])
                if abs(samples).max() < 0.0001:
                    raise ValueError("The recording is silent. Try an audible source.")
                media.write_audio(normalized, samples)
                info = audio_features(normalized, project["duration"])
                info.update(
                    kind="audio",
                    original_duration=original_duration,
                    excerpt_start=0,
                    excerpt_end=min(original_duration, project["duration"]),
                    padding="silence" if original_duration < project["duration"] else None,
                )
            row = {
                "id": identity,
                "project_id": project_id,
                "user_id": project["user_id"],
                "role": role,
                "name": safe_name,
                "original_path": self.store.relative(original),
                "path": self.store.relative(normalized),
                "sha256": media.digest(original),
                "normalized_sha256": media.digest(normalized),
                "analysis": info,
                "created_at": now(),
            }
            with self.store.connect() as db:
                db.execute(
                    "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    tuple(packed(v) if k == "analysis" else v for k, v in row.items()),
                )
                Store.event(
                    db,
                    project_id,
                    project["user_id"],
                    "asset_contributed",
                    {"asset_id": identity, "role": role},
                )
            return row
        except Exception as error:
            shutil.rmtree(folder)
            if isinstance(error, (OSError, RuntimeError)):
                raise ValueError("This file could not be read as the selected media type.") from error
            raise

    def enqueue(self, project_id, request):
        project = self.project(project_id)
        stage = request.stage
        selected = self.selections(project_id)
        context = {s: selected[s] for s in STAGES[: STAGES.index(stage)] if s in selected}
        if len(context) != STAGES.index(stage):
            raise ValueError("Select a candidate at each earlier stage first.")
        for candidate_id in context.values():
            c = self.candidate(candidate_id)
            if c["status"] != "ready" or not self.compatible(c, selected):
                raise ValueError("An earlier selection needs to be regenerated or selected again.")
        asset_ids = list(dict.fromkeys(request.asset_ids))
        assets = [
            self.store.one("SELECT * FROM assets WHERE id=? AND project_id=?", (i, project_id))
            for i in asset_ids
        ]
        if stage == "audio":
            if sum(a["role"] == "reference" for a in assets) != 1:
                raise ValueError("Choose exactly one personal audio reference.")
            if any(a["role"] == "photo" for a in assets) or any(
                sum(a["role"] == role for a in assets) > 1 for role in ("bed", "effect")
            ):
                raise ValueError("Choose at most one bed and one sound effect.")
        elif stage == "video":
            if not 1 <= len(assets) <= 10 or any(a["role"] != "photo" for a in assets):
                raise ValueError("Choose between 1 and 10 photographs.")
        elif asset_ids:
            raise ValueError("This stage uses earlier selected candidates, not new files.")
        if stage == "text" and not request.keyword:
            raise ValueError("Enter one Keyword.")
        batch_id, job_id, seed = uid(), uid(), secrets.randbelow(2**31 - 4)
        styles = choose_styles(stage, seed)
        if stage == "audio":
            styles.append(
                {
                    "id": "original-mix",
                    "name": "Original Mix",
                    "family": "preservation",
                    "mode": "original",
                    "bpm": 90,
                    "color": "#c7e6de",
                    "description": "Your recording, intact, with a quiet bed and sound accents.",
                }
            )
        timestamp = now()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if self._selected_in(db, project_id) != selected:
                raise ValueError("A selection changed. Refresh and generate again.")
            if db.execute(
                "SELECT 1 FROM jobs j JOIN batches b ON j.batch_id=b.id WHERE b.project_id=? AND j.status IN ('queued','running')",
                (project_id,),
            ).fetchone():
                raise ValueError("Finish the current batch before requesting another.")
            db.execute(
                "INSERT INTO batches VALUES(?,?,?,?,?,?,?)",
                (
                    batch_id,
                    project_id,
                    stage,
                    project["user_id"],
                    seed,
                    packed(request.model_dump()),
                    timestamp,
                ),
            )
            for slot, style in enumerate(styles, 1):
                settings = {
                    "style": style,
                    "seed": seed + slot,
                    "duration": project["duration"],
                    "aspect": project["aspect"],
                    "keyword": request.keyword,
                    "provider": "local",
                    "model": None,
                    "renderer_version": VERSION,
                    "presets_version": 1,
                }
                db.execute(
                    "INSERT INTO candidates(id,project_id,batch_id,stage,slot,kind,settings,context,sources,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        uid(),
                        project_id,
                        batch_id,
                        stage,
                        slot,
                        "original" if slot == 4 else "interpretation",
                        packed(settings),
                        packed(context),
                        packed(asset_ids),
                        timestamp,
                    ),
                )
            db.execute(
                "INSERT INTO jobs(id,batch_id,cost_usd,created_at) VALUES(?,?,?,?)",
                (job_id, batch_id, 0, timestamp),
            )
            Store.event(
                db,
                project_id,
                project["user_id"],
                "batch_requested",
                {"batch_id": batch_id, "context": context},
            )
        return {"batch_id": batch_id, "job_id": job_id}

    @staticmethod
    def _selected_in(db, project_id):
        return {
            r["stage"]: r["candidate_id"]
            for r in db.execute("SELECT * FROM selections WHERE project_id=?", (project_id,))
        }

    def rate(self, candidate_id, stars):
        if type(stars) is not int or stars not in range(1, 6):
            raise ValueError("Choose 1 to 5 stars.")
        c = self.candidate(candidate_id)
        p = self.project(c["project_id"])
        if c["status"] != "ready":
            raise ValueError("Wait until the candidate is ready before rating it.")
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO ratings(candidate_id,user_id,stars,created_at) VALUES(?,?,?,?)",
                (candidate_id, p["user_id"], stars, now()),
            )
            if stars == 5:
                db.execute(
                    "UPDATE candidates SET winner_at=COALESCE(winner_at,?) WHERE id=?", (now(), candidate_id)
                )
            Store.event(
                db, p["id"], p["user_id"], "candidate_rated", {"candidate_id": candidate_id, "stars": stars}
            )
        return self.candidate(candidate_id)

    def select(self, candidate_id):
        c = self.candidate(candidate_id)
        p = self.project(c["project_id"])
        if c["status"] != "ready" or c["rating"] is None:
            raise ValueError("Listen or watch, then rate this candidate before selecting it.")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            selected = self._selected_in(db, p["id"])
            if not self.compatible(c, selected):
                raise ValueError("This candidate was made for earlier selections. Regenerate this stage.")
            if selected.get(c["stage"]) == candidate_id:
                return {"selected": candidate_id}
            db.execute(
                "INSERT OR REPLACE INTO selections VALUES(?,?,?,?,?)",
                (p["id"], c["stage"], candidate_id, p["user_id"], now()),
            )
            for later in STAGES[STAGES.index(c["stage"]) + 1 :]:
                db.execute("DELETE FROM selections WHERE project_id=? AND stage=?", (p["id"], later))
            Store.event(
                db,
                p["id"],
                p["user_id"],
                "candidate_selected",
                {"candidate_id": candidate_id, "stage": c["stage"], "previous": selected},
            )
        return {"selected": candidate_id}

    def retry(self, job_id):
        job = self.store.one("SELECT * FROM jobs WHERE id=?", (job_id,))
        if job["status"] != "failed":
            raise ValueError("Only a failed batch can be retried.")
        batch = self.store.one("SELECT * FROM batches WHERE id=?", (job["batch_id"],))
        identity = uid()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM jobs j JOIN batches b ON j.batch_id=b.id WHERE b.project_id=? AND j.status IN ('queued','running')",
                (batch["project_id"],),
            ).fetchone():
                raise ValueError("This project already has an active batch.")
            remaining = db.execute(
                "SELECT 1 FROM candidates WHERE batch_id=? AND status!='ready'", (job["batch_id"],)
            ).fetchone()
            if not remaining:
                raise ValueError("Every candidate in this batch is already complete.")
            attempt = db.execute(
                "SELECT MAX(attempt)+1 FROM jobs WHERE batch_id=?", (job["batch_id"],)
            ).fetchone()[0]
            db.execute(
                "INSERT INTO jobs(id,batch_id,attempt,cost_usd,created_at) VALUES(?,?,?,?,?)",
                (identity, job["batch_id"], attempt, 0, now()),
            )
            db.execute(
                "UPDATE candidates SET status='queued',error=NULL WHERE batch_id=? AND status!='ready'",
                (job["batch_id"],),
            )
            Store.event(
                db,
                batch["project_id"],
                batch["user_id"],
                "retry_requested",
                {"job_id": identity, "previous_job": job_id},
            )
        return {"job_id": identity}

    def approve(self, project_id, request):
        p = self.project(project_id)
        c = self.candidate(request.candidate_id)
        if c["project_id"] != project_id or c["stage"] != "assembly" or c["status"] != "ready":
            raise ValueError("Choose a completed final mix from this project.")
        if not request.confirmed or len(request.explanation.strip()) < 5:
            raise ValueError("Explain why this one, then explicitly approve it.")
        # Verify the exact final artifact at approval, not just a successful past job.
        artifact = c["artifacts"].get("output", {})
        if not artifact or media.digest(self.store.path(artifact["path"])) != artifact["sha256"]:
            raise ValueError("The final file changed or is missing. Generate it again before approval.")
        identity, timestamp = uid(), now()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            selected = self._selected_in(db, project_id)
            if selected.get("assembly") != c["id"] or not self.compatible(c, selected):
                raise ValueError("Select this final mix using the current ingredients before approving it.")
            if (
                db.execute(
                    "SELECT COUNT(*) FROM candidates WHERE batch_id=? AND status='ready'", (c["batch_id"],)
                ).fetchone()[0]
                != 3
            ):
                raise ValueError("Wait until all three final mixes are ready to compare.")
            snapshot = {
                "schema_version": 1,
                "app_version": VERSION,
                "project": p,
                "made_by": p["author"],
                "approved_by": p["author"],
                "approved_at": timestamp,
                "why_this_one": request.explanation,
                "approval_id": identity,
                "selected_version": c["id"],
                "selections": selected,
                "identity_method": "declared local author; not authenticated",
                "final_sha256": artifact["sha256"],
            }
            for key, sql in {
                "source_assets": "SELECT * FROM assets WHERE project_id=?",
                "candidates_considered": "SELECT * FROM candidates WHERE project_id=?",
                "batches": "SELECT * FROM batches WHERE project_id=?",
                "ratings": "SELECT r.* FROM ratings r JOIN candidates c ON r.candidate_id=c.id WHERE c.project_id=?",
                "jobs": "SELECT j.* FROM jobs j JOIN batches b ON j.batch_id=b.id WHERE b.project_id=?",
                "events": "SELECT * FROM events WHERE project_id=? ORDER BY id",
            }.items():
                snapshot[key] = [unpack(row) for row in db.execute(sql, (project_id,))]
            db.execute(
                "INSERT INTO approvals VALUES(?,?,?,?,?,?,?)",
                (
                    identity,
                    project_id,
                    c["id"],
                    p["user_id"],
                    request.explanation,
                    packed(snapshot),
                    timestamp,
                ),
            )
            Store.event(
                db,
                project_id,
                p["user_id"],
                "final_approved",
                {"approval_id": identity, "candidate_id": c["id"]},
            )
        return {"approval_id": identity}

    def export(self, approval_id):
        approval = self.store.one("SELECT * FROM approvals WHERE id=?", (approval_id,))
        snapshot = approval["snapshot"]
        final = next(c for c in snapshot["candidates_considered"] if c["id"] == approval["candidate_id"])
        source = self.store.path(final["artifacts"]["output"]["path"])
        if media.digest(source) != snapshot["final_sha256"]:
            raise ValueError("The approved media changed. Export stopped to protect the approval record.")
        identity = uid()
        target = self.store.path(f"exports/{identity}.zip")
        target.parent.mkdir(exist_ok=True)
        manifest = packed(snapshot)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(source, "approved.mp4")
            bundle.writestr("provenance.json", manifest)
            bundle.writestr(
                "READ-ME.txt",
                f"MIT 2.009 — {snapshot['project']['name']}\nMade and approved by: {snapshot['approved_by']}\nWhy this one? {snapshot['why_this_one']}\nApproved at: {snapshot['approved_at']}\nSource files are identified in provenance.json and are not included.\n",
            )
        with self.store.connect() as db:
            db.execute(
                "INSERT INTO exports VALUES(?,?,?,?,?)",
                (identity, approval_id, self.store.relative(target), media.digest(target), now()),
            )
            Store.event(
                db,
                approval["project_id"],
                approval["user_id"],
                "approved_export_created",
                {"export_id": identity, "approval_id": approval_id},
            )
        return {"export_id": identity, "url": f"/api/exports/{identity}/file"}
