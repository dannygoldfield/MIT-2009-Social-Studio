"""Cheap, explicitly heuristic features; these never measure artistic quality."""

import numpy as np

from .media import SAMPLE_RATE, read_audio


def audio_features(path, duration=15):
    audio = read_audio(path, duration)
    mono = audio.mean(axis=1)
    hop = SAMPLE_RATE // 50
    if len(mono) < hop:
        raise ValueError("Use a recording at least 20 milliseconds long.")
    count = len(mono) // hop
    rms = np.sqrt(np.mean(mono[: count * hop].reshape(count, hop) ** 2, axis=1))
    novelty = np.maximum(0, np.diff(rms, prepend=rms[0]))
    peaks = []
    threshold = max(0.003, float(np.percentile(novelty, 82)))
    for i in range(1, len(novelty) - 1):
        t = i / 50
        if novelty[i] > threshold and novelty[i] >= max(novelty[i - 1], novelty[i + 1]):
            if not peaks or t - peaks[-1] >= 0.2:
                peaks.append(round(t, 3))
    intervals = np.diff(peaks)
    tempo = None
    confidence = 0.0
    if len(intervals) >= 3:
        median = float(np.median(intervals))
        consistency = float(np.mean(np.abs(intervals - median) < 0.1))
        if consistency >= 0.65 and 0.25 <= median <= 1.2:
            tempo = round(60 / median, 1)
            confidence = round(consistency, 2)
    return {
        "method": "rms-onset-heuristic-v1",
        "tempo_bpm": tempo,
        "tempo_confidence": confidence,
        "onsets_seconds": peaks,
        "energy": [round(float(x), 4) for x in rms[::10]],
        "rms": round(float(np.sqrt(np.mean(mono**2))), 5),
        "peak": round(float(np.max(np.abs(audio))), 5),
        "note": "Onsets are energy changes, not verified musical beats. Tempo may be unknown.",
    }


def image_features(image):
    pixels = np.asarray(image.resize((96, 96))).astype(float) / 255
    luma = pixels @ np.array([0.2126, 0.7152, 0.0722])
    edges = abs(np.diff(luma, axis=1)).mean()
    bands = np.array_split(luma, 3)
    quiet = int(np.argmin([b.std() for b in bands]))
    return {
        "method": "thumbnail-statistics-v1",
        "mean_rgb": pixels.mean(axis=(0, 1)).round(4).tolist(),
        "luminance": round(float(luma.mean()), 4),
        "tonal_spread": round(float(luma.std()), 4),
        "edge_density": round(float(edges), 4),
        "quiet_band": ["top", "center", "bottom"][quiet],
        "note": "Quiet band is low tonal variation; it is not a face or subject detector.",
    }
