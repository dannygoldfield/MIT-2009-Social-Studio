"""Providers produce artifacts; they never rate, select, or approve them."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AudioRequest:
    reference: Path
    bed: Path | None
    effect: Path | None
    style: dict
    duration: float
    seed: int


@dataclass
class AudioResult:
    output: Path
    metadata: dict


class AudioProvider(Protocol):
    name: str

    def generate(self, request: AudioRequest, folder: Path) -> AudioResult: ...
