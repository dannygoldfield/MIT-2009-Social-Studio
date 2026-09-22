import numpy as np
import pytest
from fastapi.testclient import TestClient

from mit2009_studio import media
from mit2009_studio.demo import make_sources
from mit2009_studio.models import Generate, NewProject
from mit2009_studio.server import create_app


def test_opening_silence_keeps_quiet_notes_and_internal_rests():
    y = np.zeros((3 * media.SAMPLE_RATE, 2), dtype=np.float32)
    y[48000:60000] = 0.0005  # A soft first note before a louder one.
    y[96000:108000] = 0.2
    start = media.playback_start(y)
    assert abs(start / media.SAMPLE_RATE - 0.995) < 0.001
    shifted = y[start:]
    assert np.count_nonzero(shifted[60000 - start : 96000 - start]) == 0
    assert media.playback_start(np.zeros((48000, 2))) == 0
    assert media.playback_start(np.ones((48000, 2)) * 0.05) == 0


@pytest.mark.media
def test_candidate_playback_preserves_master_and_original(tmp_path):
    app = create_app(tmp_path / "studio", start_worker=False)
    studio = app.state.studio
    source, _ = make_sources(tmp_path / "fixtures")
    media.write_audio(source, np.concatenate((np.zeros((96000, 2)), media.read_audio(source))))
    project = studio.create_project(NewProject(name="Playback", author="Test"))
    asset = studio.add_asset(project["id"], "reference", source.name, source)
    studio.enqueue(project["id"], Generate(stage="audio", asset_ids=[asset["id"]]))
    app.state.worker.perform(app.state.worker.claim())
    with TestClient(app) as client:
        candidates = studio.detail(project["id"])["candidates"]
        assert len(candidates) == 4
        for candidate in candidates:
            assert candidate["status"] == "ready", candidate["error"]
            url = f"/api/candidates/{candidate['id']}/file/"
            original = studio.store.path(candidate["artifacts"]["output"]["path"])
            before = media.digest(original)
            response = client.get(url + "preview?playback=1")
            assert response.status_code == 200
            path = tmp_path / "playback.wav"
            path.write_bytes(response.content)
            assert media.playback_start(media.read_audio(path)) < media.SAMPLE_RATE * 0.02
            assert media.digest(original) == before
            assert client.get(url + "output?playback=1").content == original.read_bytes()
            media.verify_output(original, 15, audio=True)
        assert media.digest(studio.store.path(asset["original_path"])) == asset["sha256"]


@pytest.mark.media
def test_listening_copy_retains_every_sample_after_opening(studio, tmp_path):
    source = tmp_path / "phrase.wav"
    y = np.zeros((3 * media.SAMPLE_RATE, 2), dtype=np.float32)
    y[48000:60000] = 0.0005
    y[96000:108000] = 0.2
    media.write_audio(source, y)
    before = media.digest(source)
    original = media.read_audio(source)
    start = media.playback_start(original)
    preview = studio.playback_audio(source)
    actual = media.read_audio(preview)
    assert len(actual) == len(original) - start
    np.testing.assert_allclose(actual, original[start:], atol=1 / 32767)
    assert studio.playback_audio(source) == preview
    assert media.digest(source) == before
