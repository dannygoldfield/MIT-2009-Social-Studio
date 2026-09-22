import json
import os
import random
from pathlib import Path


def load_presets():
    path = Path(os.environ.get("STUDIO_PRESETS", Path(__file__).with_name("presets.json")))
    presets = json.loads(path.read_text())
    for stage in ("audio", "video", "text", "assembly"):
        entries = presets.get(stage, [])
        if len({p["id"] for p in entries}) != len(entries) or len({p["family"] for p in entries}) < 3:
            raise ValueError(f"{stage} needs unique preset IDs and at least three different families.")
    return presets


def choose_styles(stage, seed):
    rng = random.Random(seed)
    entries = load_presets()[stage]
    families = sorted({p["family"] for p in entries})
    selected = rng.sample(families, 3)
    return [rng.choice([p for p in entries if p["family"] == family]) for family in selected]
