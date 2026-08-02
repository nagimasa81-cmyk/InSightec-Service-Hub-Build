from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

@dataclass(slots=True)
class SourceStatus:
    path: str | None = None
    loaded: bool = False
    records: int = 0
    error: str | None = None

@dataclass(slots=True)
class MRMetadata:
    fields: dict[str, Any] = field(default_factory=dict)
    source: SourceStatus = field(default_factory=SourceStatus)

@dataclass(slots=True)
class TimingMetadata:
    mr_scan_start: str | None = None
    mr_scan_end: str | None = None
    sonication_start: str | None = None
    sonication_end: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class SkullMetadata:
    files: list[str] = field(default_factory=list)
    spot_cues: list[str] = field(default_factory=list)
    element_counts: dict[str, int] = field(default_factory=dict)

@dataclass(slots=True)
class SonicationMetadata:
    index: int
    summary: dict[str, Any] = field(default_factory=dict)
    protocol: dict[str, Any] = field(default_factory=dict)
    spots: list[dict[str, Any]] = field(default_factory=list)
    treatment: dict[str, Any] = field(default_factory=dict)
    layer: dict[str, Any] = field(default_factory=dict)
    mr: MRMetadata = field(default_factory=MRMetadata)
    timing: TimingMetadata = field(default_factory=TimingMetadata)
    skull: SkullMetadata = field(default_factory=SkullMetadata)
    sources: dict[str, SourceStatus] = field(default_factory=dict)

@dataclass(slots=True)
class StudyMetadata:
    root: str
    study: dict[str, Any] = field(default_factory=dict)
    mr: MRMetadata = field(default_factory=MRMetadata)
    sonications: dict[int, SonicationMetadata] = field(default_factory=dict)
    sources: dict[str, SourceStatus] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
