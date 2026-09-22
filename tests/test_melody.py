import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from mit2009_studio import media
from mit2009_studio.demo import make_sources
from mit2009_studio.melody import extract_notes, prepare_guide, synthesize_guide
from mit2009_studio.server import create_app


@pytest.mark.media
def test_known_melody_survives_note_extraction(tmp_path):
    source, _ = make_sources(tmp_path / "source")
    guide, score = prepare_guide(source, tmp_path / "guide")
    pitches = [n["midi"] for n in score["notes"]]
    assert pitches == [60, 64, 67, 69, 67, 64, 62, 60]
    assert abs(score["notes"][3]["start"] - 2.25) < 0.2
    assert score["source_audio_in_output"] is False
    assert media.digest(guide) == score["guide_sha256"]
    media.verify_output(guide, 15, audio=True)
    assert np.max(np.abs(media.read_audio(guide))) < 1


@pytest.mark.media
def test_noise_is_not_invented_into_a_melody(tmp_path):
    path = tmp_path / "noise.wav"
    media.write_audio(path, np.random.default_rng(2).normal(0, 0.05, (96000, 2)))
    with pytest.raises(ValueError, match="couldn't follow"):
        extract_notes(path)


def test_guide_synthesis_accepts_only_notes_and_timing():
    notes = [{"midi": 60, "start": 0.2, "duration": 0.5}]
    rendered = synthesize_guide(notes, 2)
    # A different source waveform cannot enter this function. Non-note annotations
    # also cannot leak syllable envelopes or confidence into the synthesized sound.
    annotated = [{**notes[0], "confidence": 0.1, "source_label": "different singer"}]
    assert np.array_equal(rendered, synthesize_guide(annotated, 2))
    assert np.count_nonzero(rendered[:9600]) == 0
    assert np.count_nonzero(rendered[33600:]) == 0


@pytest.mark.media
def test_melody_api_persists_guide_and_retires_voice_effects(tmp_path):
    source, _ = make_sources(tmp_path / "source")
    app = create_app(tmp_path / "studio", start_worker=False)
    headers = {"X-Studio-Request": "1"}
    with TestClient(app) as client:
        p = client.post("/api/projects", json={"name": "Melody", "author": "Test"}, headers=headers).json()
        with source.open("rb") as audio:
            a = client.post(
                f"/api/projects/{p['id']}/assets",
                data={"role": "reference"},
                files={"file": (source.name, audio, "audio/wav")},
                headers=headers,
            ).json()
        guide = client.post(f"/api/assets/{a['id']}/melody", headers=headers)
        assert guide.status_code == 200
        saved = guide.json()
        assert saved["source_audio_in_output"] is False
        assert client.get(saved["url"]).headers["content-type"] == "audio/wav"
        assert client.post(f"/api/assets/{a['id']}/melody", headers=headers).json() == saved
        detail = client.get(f"/api/projects/{p['id']}").json()
        assert detail["assets"][0]["analysis"]["melody_guide"] == saved
        assert detail["candidates"] == [] and detail["approvals"] == []
        assert (
            client.post(
                f"/api/projects/{p['id']}/generate",
                json={"stage": "audio", "asset_ids": [a["id"]]},
                headers=headers,
            ).status_code
            == 409
        )
        with source.open("rb") as audio:
            assert (
                client.post(
                    f"/api/projects/{p['id']}/assets",
                    data={"role": "bed"},
                    files={"file": (source.name, audio, "audio/wav")},
                    headers=headers,
                ).status_code
                == 400
            )
        score = json.loads(app.state.studio.store.path(saved["score_path"]).read_text())
        assert score["guide_sha256"] == saved["sha256"]
