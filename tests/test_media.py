import numpy as np
import pytest

from mit2009_studio import media
from mit2009_studio.demo import make_sources
from mit2009_studio.jobs import Worker
from mit2009_studio.models import Approval, Generate, NewProject


@pytest.mark.media
@pytest.mark.parametrize("aspect,size", [("vertical", (180, 320)), ("horizontal", (320, 180))])
def test_real_end_to_end_media(studio, tmp_path, aspect, size):
    project = studio.create_project(
        NewProject(name="Codec verification", author="Automated test only", aspect=aspect)
    )
    audio, photos = make_sources(tmp_path / "fixtures")
    a = studio.add_asset(project["id"], "reference", audio.name, audio)
    pics = [studio.add_asset(project["id"], "photo", p.name, p) for p in photos]
    worker = Worker(studio, size_override=size)
    for stage in ("audio", "video", "text", "assembly"):
        ids = [a["id"]] if stage == "audio" else [p["id"] for p in pics] if stage == "video" else []
        batch = studio.enqueue(
            project["id"], Generate(stage=stage, asset_ids=ids, keyword="CONNECT" if stage == "text" else "")
        )
        job = worker.claim()
        assert job["id"] == batch["job_id"]
        worker.perform(job)
        done = studio.store.one("SELECT * FROM jobs WHERE id=?", (job["id"],))
        assert done["status"] == "done", done["error"]
        candidates = studio.store.all(
            "SELECT * FROM candidates WHERE batch_id=? ORDER BY slot", (batch["batch_id"],)
        )
        assert len(candidates) == (4 if stage == "audio" else 3)
        assert len({c["artifacts"]["output"]["sha256"] for c in candidates}) == len(candidates)
        for c in candidates:
            path = studio.store.path(c["artifacts"]["output"]["path"])
            verified = media.verify_output(
                path,
                15,
                size if stage != "audio" else None,
                alpha=stage == "text",
                audio=stage in ("audio", "assembly"),
            )
            assert abs(verified["duration"] - 15) < 0.08
            if stage == "text":
                raw = media.ff(
                    ["-ss", 3, "-i", path, "-frames:v", 1, "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"]
                )
                alpha = np.frombuffer(raw, np.uint8).reshape(size[1], size[0], 4)[:, :, 3]
                assert alpha.min() == 0 and alpha.max() > 240
            if stage in ("video", "assembly"):
                stream = next(s for s in media.probe(path)["streams"] if s["codec_type"] == "video")
                assert stream["nb_frames"] == "450"
                assert stream["avg_frame_rate"] == "30/1"
            if stage == "audio":
                samples = media.read_audio(path)
                assert np.max(abs(samples)) < 1 and np.mean(samples**2) > 0.000001
        if stage == "audio":
            original_samples = media.read_audio(
                studio.store.path(candidates[3]["artifacts"]["output"]["path"])
            )
            source = media.read_audio(audio)
            assert np.corrcoef(source[:, 0], original_samples[: len(source), 0])[0, 1] > 0.98
        chosen = candidates[0]
        studio.rate(chosen["id"], 5)
        studio.select(chosen["id"])
    approved = studio.approve(
        project["id"],
        Approval(
            candidate_id=chosen["id"],
            explanation="AUTOMATED TEST: verify approval and export only.",
            confirmed=True,
        ),
    )
    assert studio.export(approved["approval_id"])["export_id"]
