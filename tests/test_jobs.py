import pytest

from mit2009_studio.jobs import Worker
from mit2009_studio.media import digest
from mit2009_studio.models import Generate
from mit2009_studio.store import packed


def test_interrupted_job_requires_explicit_retry_and_retains_completed_candidate(
    studio, project, source_assets
):
    batch = studio.enqueue(project["id"], Generate(stage="audio", asset_ids=[source_assets[0]["id"]]))
    worker = Worker(studio, size_override=(180, 320))
    job = worker.claim()
    candidates = studio.store.all(
        "SELECT * FROM candidates WHERE batch_id=? ORDER BY slot", (batch["batch_id"],)
    )
    # Simulate a process ending after its first output committed.
    saved = studio.store.path("already-finished.wav")
    saved.write_bytes(b"completed-output")
    artifacts = packed({"output": {"path": saved.name, "sha256": digest(saved)}})
    with studio.store.connect() as db:
        db.execute(
            "UPDATE candidates SET status='ready',artifacts=? WHERE id=?", (artifacts, candidates[0]["id"])
        )
        db.execute("UPDATE candidates SET status='running' WHERE id=?", (candidates[1]["id"],))
    worker.start()
    try:
        recovered = studio.store.one("SELECT * FROM jobs WHERE id=?", (job["id"],))
        assert recovered["status"] == "failed"
        assert studio.candidate(candidates[0]["id"])["status"] == "ready"
        assert studio.candidate(candidates[1]["id"])["status"] == "failed"
        assert saved.read_bytes() == b"completed-output"
        # No hidden auto-retry and only one process owns this data folder.
        with pytest.raises(RuntimeError, match="another studio"):
            Worker(studio).start()
    finally:
        worker.stop()
    retry = studio.retry(job["id"])
    attempt = studio.store.one("SELECT * FROM jobs WHERE id=?", (retry["job_id"],))
    assert attempt["attempt"] == 2
    assert studio.candidate(candidates[0]["id"])["status"] == "ready"
    assert studio.candidate(candidates[1]["id"])["status"] == "queued"
    with pytest.raises(ValueError, match="active batch"):
        studio.retry(job["id"])


def test_job_preserves_other_candidates_when_renderer_fails(studio, project, source_assets, monkeypatch):
    from mit2009_studio import jobs

    batch = studio.enqueue(project["id"], Generate(stage="audio", asset_ids=[source_assets[0]["id"]]))

    def failed(*args):
        raise RuntimeError("Deliberate renderer failure")

    monkeypatch.setitem(jobs.RENDERERS, "audio", failed)
    worker = Worker(studio)
    worker.perform(worker.claim())
    result = studio.store.one("SELECT * FROM jobs WHERE id=?", (batch["job_id"],))
    assert result["status"] == "failed"
    assert "Deliberate renderer failure" in result["error"]
    assert len(studio.store.all("SELECT * FROM candidates WHERE status='failed'")) == 4
