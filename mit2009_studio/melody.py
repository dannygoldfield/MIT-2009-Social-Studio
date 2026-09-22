"""Turn a monophonic phrase into a note-only guide, never an orchestration claim."""

import json
from pathlib import Path

import librosa
import numpy as np
from scipy.ndimage import median_filter

from . import media

METHOD = "pyin-note-guide-v1"


def extract_notes(path, duration=15):
    rate, hop = 16000, 256
    raw = media.ff(["-i", path, "-t", duration, "-vn", "-ar", rate, "-ac", 1, "-f", "f32le", "pipe:1"])
    y = np.frombuffer(raw, dtype="<f4").copy()
    if len(y) < rate * 0.2 or np.max(np.abs(y), initial=0) < 0.0001:
        raise ValueError("Try a longer hum or sung phrase so we can hear its notes.")
    f0, voiced, probability = librosa.pyin(
        y, sr=rate, fmin=65, fmax=880, frame_length=2048, hop_length=hop, fill_na=np.nan
    )
    valid = voiced & np.isfinite(f0) & (probability >= 0.15)
    pitches = np.full(len(f0), -1, dtype=int)
    pitches[valid] = np.rint(69 + 12 * np.log2(f0[valid] / 440)).astype(int)
    # Bridge only brief gaps between the same note; do not invent missing phrases.
    for i in range(1, len(pitches) - 1):
        if pitches[i] < 0 and pitches[i - 1] >= 0:
            stop = i
            while stop < min(len(pitches), i + 5) and pitches[stop] < 0:
                stop += 1
            if stop < len(pitches) and pitches[stop] == pitches[i - 1]:
                pitches[i:stop] = pitches[i - 1]
    pitches = median_filter(pitches, size=5, mode="nearest")
    notes = []
    start = 0
    for end in range(1, len(pitches) + 1):
        if end < len(pitches) and pitches[end] == pitches[start]:
            continue
        seconds = min(end * hop / rate, duration, len(y) / rate) - start * hop / rate
        if pitches[start] >= 0 and seconds >= 0.08:
            notes.append(
                {
                    "midi": int(pitches[start]),
                    "start": round(start * hop / rate, 4),
                    "duration": round(seconds, 4),
                    "confidence": round(float(np.mean(probability[start:end])), 3),
                }
            )
        start = end
    if not notes or sum(n["duration"] for n in notes) < 0.2:
        raise ValueError(
            "We couldn't follow enough notes yet. Try humming one phrase on its own, without background music."
        )
    return {
        "method": METHOD,
        "library": f"librosa {librosa.__version__}",
        "duration": duration,
        "notes": notes,
        "source_audio_in_output": False,
        "voiced_coverage": round(float(np.mean(valid)), 3),
        "note": "Estimated notes and timing, not a musical-ability score. Octaves and notes may need correction. This is a melody guide, not an ensemble performance.",
    }


def synthesize_guide(notes, duration=15):
    """Only note numbers and timing cross this boundary. No source samples or lyrics."""
    output = np.zeros(round(duration * media.SAMPLE_RATE))
    for note in notes:
        start = round(note["start"] * media.SAMPLE_RATE)
        count = min(round(note["duration"] * media.SAMPLE_RATE), len(output) - start)
        if count <= 0:
            continue
        t = np.arange(count) / media.SAMPLE_RATE
        frequency = 440 * 2 ** ((note["midi"] - 69) / 12)
        envelope = np.minimum(1, t / 0.012) * np.minimum(1, (count / media.SAMPLE_RATE - t) / 0.035)
        phase = 2 * np.pi * frequency * t
        tone = np.sin(phase) + 0.16 * np.sin(phase * 2) + 0.04 * np.sin(phase * 3)
        output[start : start + count] += tone * envelope * 0.24
    return np.column_stack((output, output))


def prepare_guide(source, folder, duration=15):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    score = extract_notes(source, duration)
    output = folder / "melody-guide.wav"
    media.write_audio(output, synthesize_guide(score["notes"], duration))
    score["source_sha256"] = media.digest(source)
    score["guide_sha256"] = media.digest(output)
    media.verify_output(output, duration, audio=True)
    (folder / "melody.json").write_text(json.dumps(score, indent=2))
    return output, score
