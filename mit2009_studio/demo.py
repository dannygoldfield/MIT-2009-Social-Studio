"""Rights-clear practice material generated locally; no student media ships in Git."""

import argparse
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import media
from .models import NewProject
from .service import Studio


def make_sources(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    audio = folder / "sample-melody.wav"
    rate = media.SAMPLE_RATE
    t = np.arange(6 * rate) / rate
    notes = np.array([261.63, 329.63, 392, 440, 392, 329.63, 293.66, 261.63])
    indexes = np.minimum((t / 0.75).astype(int), len(notes) - 1)
    phase = np.cumsum(notes[indexes]) * 2 * np.pi / rate
    envelope = np.sin(np.pi * ((t % 0.75) / 0.75)) ** 2
    signal = 0.24 * envelope * (np.sin(phase) + 0.2 * np.sin(2 * phase))
    media.write_audio(audio, np.column_stack((signal, signal)))
    photos = []
    colors = [("#cbd96e", "#315a56"), ("#af9bcf", "#4d3d62"), ("#edb089", "#8b4e35")]
    for i, (background, foreground) in enumerate(colors):
        image = Image.new("RGB", (960, 720), background)
        draw = ImageDraw.Draw(image)
        for n in range(9):
            x = 60 + n * 100
            y = 150 + round(np.sin(n + i) * 80)
            draw.rounded_rectangle((x, y, x + 65, y + 340), radius=30, fill=foreground)
            draw.ellipse((x - 15, y + 20, x + 85, y + 120), fill="#f7f2dc")
        draw.text((35, 35), f"PRACTICE IMAGE {i + 1} / GENERATED GEOMETRY", fill=foreground)
        path = folder / f"practice-{i + 1}.jpg"
        image.save(path, quality=92)
        photos.append(path)
    return audio, photos


def create_demo(studio):
    project = studio.create_project(
        NewProject(name="Practice · Make connections", author="Demo author (practice)", aspect="vertical")
    )
    with tempfile.TemporaryDirectory(dir=studio.store.root) as folder:
        audio, photos = make_sources(folder)
        studio.add_asset(project["id"], "reference", audio.name, audio)
        for photo in photos:
            studio.add_asset(project["id"], "photo", photo.name, photo)
    return project


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/candidate-engine"))
    args = parser.parse_args()
    project = create_demo(Studio(args.data_dir))
    print(f"Practice project created: {project['id']}. Open the studio to make your choices.")


if __name__ == "__main__":
    main()
