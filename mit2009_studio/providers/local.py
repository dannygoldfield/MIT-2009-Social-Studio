"""Auditable local sound transformations. This is DSP, not a learned AI model."""

import numpy as np

from .. import media
from . import AudioRequest, AudioResult


def procedural_bed(count, bpm, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(count) / media.SAMPLE_RATE
    pulse = np.zeros(count)
    beat = 60 / bpm
    for i, start in enumerate(np.arange(0, count / media.SAMPLE_RATE, beat)):
        n = int(start * media.SAMPLE_RATE)
        length = min(int(0.16 * media.SAMPLE_RATE), count - n)
        local = np.arange(length) / media.SAMPLE_RATE
        if i % 2:
            sound = rng.normal(0, 1, length) * np.exp(-local * 45) * 0.022
        else:
            sound = (
                np.sin(2 * np.pi * (75 * local + 2 * (1 - np.exp(-local * 30)))) * np.exp(-local * 25) * 0.055
            )
        pulse[n : n + length] += sound
    drone = 0.014 * np.sin(2 * np.pi * 130.81 * t) + 0.009 * np.sin(2 * np.pi * 196 * t)
    return np.column_stack((pulse + drone, pulse + np.roll(drone, 240)))


def pitch(samples, count, rate):
    positions = (np.arange(count) * rate) % len(samples)
    return np.column_stack(
        [np.interp(positions, np.arange(len(samples)), samples[:, channel]) for channel in (0, 1)]
    )


def echo(samples, delays):
    out = samples.copy()
    for seconds, gain in delays:
        offset = int(seconds * media.SAMPLE_RATE)
        if offset < len(out):
            out[offset:] += samples[:-offset] * gain
    return out


class LocalAudioProvider:
    name = "local-dsp"

    def generate(self, request: AudioRequest, folder):
        count = round(request.duration * media.SAMPLE_RATE)
        source = media.read_audio(request.reference, request.duration)
        reference = media.fit_audio(source, count)
        mode = request.style["mode"]
        bpm = request.style.get("bpm", 100)
        t = np.arange(count) / media.SAMPLE_RATE
        rng = np.random.default_rng(request.seed)
        if mode == "original":
            transformed = reference.copy()
        elif mode == "echo":
            transformed = echo(reference * 0.72, [(0.375, 0.5), (0.75, 0.3), (1.5, 0.16)])
        elif mode in ("chop", "spark"):
            transformed = np.zeros_like(reference)
            length = int(media.SAMPLE_RATE * (60 / bpm) * (0.42 if mode == "spark" else 0.8))
            window = np.hanning(length)[:, None]
            for start in np.arange(0, request.duration, 60 / bpm / (2 if mode == "spark" else 1)):
                origin = int(rng.integers(0, max(1, len(source) - length)))
                fragment = media.fit_audio(source[origin : origin + length], length) * window
                n = int(start * media.SAMPLE_RATE)
                transformed[n : min(count, n + length)] += fragment[: count - n]
            transformed = echo(transformed, [(0.19, 0.25)])
        elif mode == "reverse":
            transformed = echo(pitch(source[::-1], count, 0.8), [(0.6, 0.4), (1.3, 0.25)])
        elif mode == "ring":
            transformed = pitch(source, count, 1.25) * np.sin(2 * np.pi * 31 * t)[:, None]
        elif mode == "radio":
            intermediate = folder / "radio.wav"
            media.ff(["-i", request.reference, "-af", "highpass=f=450,lowpass=f=2400", intermediate])
            transformed = media.fit_audio(media.read_audio(intermediate, request.duration), count, loop=True)
            transformed = np.tanh(transformed * 2) * 0.55
        elif mode == "elastic":
            positions = np.cumsum(1 + 0.35 * np.sin(2 * np.pi * 0.4 * t)) % len(source)
            transformed = np.column_stack(
                [np.interp(positions, np.arange(len(source)), source[:, ch]) for ch in (0, 1)]
            )
        elif mode == "drone":
            transformed = echo(pitch(source, count, 0.5), [(1, 0.6), (2.2, 0.3)]) * 0.7
        elif mode == "tremolo":
            transformed = pitch(source, count, 1) * (0.5 + 0.5 * np.sin(2 * np.pi * bpm / 60 * t))[:, None]
            transformed[:, 0] *= 0.7 + 0.3 * np.sin(t * 2)
            transformed[:, 1] *= 0.7 - 0.3 * np.sin(t * 2)
        else:
            raise ValueError(f"Unknown audio style mode: {mode}")
        bed = (
            media.fit_audio(media.read_audio(request.bed, request.duration), count, loop=True) * 0.16
            if request.bed
            else procedural_bed(count, bpm, request.seed)
        )
        if mode == "original":
            bed *= 0.45
        effects = np.zeros_like(reference)
        if request.effect:
            sound = media.read_audio(request.effect, request.duration) * (0.1 if mode == "original" else 0.22)
            start = min(int(media.SAMPLE_RATE * 2.0), count - 1)
            effects[start : start + min(len(sound), count - start)] = sound[: count - start]
        else:
            for at in (3.4, 9.4, 13.2):
                start = int(at * media.SAMPLE_RATE)
                length = min(int(0.12 * media.SAMPLE_RATE), count - start)
                if length > 0:
                    time = np.arange(length) / media.SAMPLE_RATE
                    ping = np.sin(2 * np.pi * 880 * time) * np.exp(-time * 45) * 0.012
                    effects[start : start + length] += ping[:, None]
        combined = transformed + bed + effects
        scale = min(1, 0.9 / max(0.00001, float(np.max(np.abs(combined)))))
        raw = folder / "unmastered.wav"
        media.write_audio(raw, combined * scale)
        output = folder / "audio.wav"
        mastering = media.master_audio(raw, output)
        raw.unlink()
        return AudioResult(
            output,
            {
                "provider": self.name,
                "model": None,
                "cost_usd": 0,
                "transformation": mode,
                "source_preserved": mode == "original",
                "mix_gain": scale,
                "bed_origin": "uploaded" if request.bed else "procedural synthesis",
                "effects_origin": "uploaded" if request.effect else "procedural synthesis",
                "rhythm_grid_bpm": bpm,
                "rhythm_grid_method": "preset, not inferred from the reference",
                "mastering": mastering,
            },
        )
