from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RawFrame:
    path: Path
    index: int
    prefix: str


@dataclass(slots=True)
class SonicationModel:
    name: str
    folder: Path
    temperature_frames: list[RawFrame] = field(default_factory=list)
    magnitude_frames: list[RawFrame] = field(default_factory=list)
    spectrum_files: list[Path] = field(default_factory=list)
    act_files: list[Path] = field(default_factory=list)
    other_files: list[Path] = field(default_factory=list)
    main_frequency_hz: float | None = None
    main_frequency_source: Path | None = None
    main_frequency_raw_line: str | None = None
    planned_duration_s: float | None = None
    actual_duration_s: float | None = None
    planned_power_w: float | None = None
    timing_source: Path | None = None

    @property
    def replay_frame_count(self) -> int:
        # Replay navigation is owned by the MR acquisition timeline.
        # SpectrumMsg files are a separately sampled stream and must be mapped
        # onto the MR cursor; including them here produced dozens of cursor
        # positions that reused the same MR image, making the arrow buttons
        # appear non-functional.
        return max(
            len(self.temperature_frames),
            len(self.magnitude_frames),
            1,
        )


@dataclass(slots=True)
class ReplayPackage:
    source: Path
    workspace: Path
    sonications: list[SonicationModel] = field(default_factory=list)
    main_frequency_hz: float | None = None
    main_frequency_source: Path | None = None
    main_frequency_raw_line: str | None = None
    main_frequency_confidence: float = 0.0
    main_frequency_interpretation: str = "Unavailable"
    cpc_spectrum_files: list[Path] = field(default_factory=list)
    planning_assets: list[object] = field(default_factory=list)
