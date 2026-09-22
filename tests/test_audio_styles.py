import numpy as np
import pytest

from mit2009_studio import media
from mit2009_studio.demo import make_sources
from mit2009_studio.providers import AudioRequest
from mit2009_studio.providers.local import LocalAudioProvider
from mit2009_studio.styles import load_presets


@pytest.mark.media
@pytest.mark.parametrize("style", load_presets()["audio"], ids=lambda p: p["id"])
def test_every_audio_preset_makes_valid_distinct_sound(tmp_path, style):
    source, _ = make_sources(tmp_path / "source")
    output = tmp_path / "render"
    output.mkdir()
    provider = LocalAudioProvider()
    result = provider.generate(AudioRequest(source, None, None, style, 15, 1234), output)
    media.verify_output(result.output, 15, audio=True)
    samples = media.read_audio(result.output)
    assert len(samples) == 15 * 48000
    assert np.isfinite(samples).all() and np.max(abs(samples)) < 1
    assert np.mean(samples**2) > 0.000001
    assert result.metadata["transformation"] == style["mode"]


@pytest.mark.media
def test_uploaded_bed_and_effect_are_used(tmp_path):
    source, _ = make_sources(tmp_path / "source")
    style = {"mode": "original", "bpm": 90}
    outputs = []
    for label, bed, effect in [("plain", None, None), ("layers", source, source)]:
        folder = tmp_path / label
        folder.mkdir()
        result = LocalAudioProvider().generate(AudioRequest(source, bed, effect, style, 15, 7), folder)
        outputs.append(media.digest(result.output))
        if bed:
            assert result.metadata["bed_origin"] == result.metadata["effects_origin"] == "uploaded"
    assert outputs[0] != outputs[1]
