from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np


@dataclass(slots=True)
class ImageFrame:
    index: int
    source: Path
    pixels: np.ndarray


@dataclass(slots=True)
class TemperatureFrame:
    index: int
    source: Path
    temperature: np.ndarray
    maximum: float
    mean: float
    hotspot_x: int
    hotspot_y: int


@dataclass(slots=True)
class SpectrumFrame:
    index: int
    timestamp_s: float
    frequency_hz: np.ndarray
    amplitude: np.ndarray
    source: Path | None = None
    confidence: float = 0.0


@dataclass(slots=True)
class ReplayFrame:
    index: int
    normalized_position: float
    magnitude: ImageFrame | None = None
    temperature: TemperatureFrame | None = None
    spectrum: SpectrumFrame | None = None


@dataclass(slots=True)
class SonicationReplay:
    name: str
    folder: Path
    frames: list[ReplayFrame] = field(default_factory=list)
    act_files: list[Path] = field(default_factory=list)
    spectrum_files: list[Path] = field(default_factory=list)


class SpectrumProvider(Protocol):
    def load_frames(self, sonication_folder: Path) -> list[SpectrumFrame]:
        ...
