"""Local configuration types adapted from Danny Goldfield's audio generator."""
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Asset:
    asset_id: str
    role: str
    family: str
    path: Path
    status: str = "Active"

@dataclass(frozen=True)
class Profile:
    profile_id: str
    bed_gain_db: float = -6
    gesture_gain_db: float = -12
    music_gain_db: float = -12
    loop_crossfade_sec: float = .5
    min_gestures: int = 0
    max_gestures: int = 1
    avoid_first_sec: float = .5
    avoid_last_sec: float = .5

@dataclass(frozen=True)
class Recipe:
    recipe_id: str
    profile_id: str
    duration_sec: float
    bed_family: str | None = None
    gesture_family: str | None = None
    use_music_stem: bool = False

@dataclass(frozen=True)
class Config:
    root: Path
    generator_version: str
    sample_rate: int
    channels: int
    sample_width_bits: int
    ingredient_audit_path: Path | None
    assets: tuple[Asset, ...]
    profiles: dict[str, Profile]
    recipes: dict[str, Recipe]
