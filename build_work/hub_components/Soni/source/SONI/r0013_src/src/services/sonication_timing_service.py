from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

from src.parsers.ado_rowset import parse_ado_rowset


@dataclass(slots=True)
class SonicationTiming:
    planned_duration_s: float | None = None
    actual_duration_s: float | None = None
    planned_power_w: float | None = None
    source: Path | None = None

    @property
    def best_duration_s(self) -> float | None:
        if self.actual_duration_s is not None and self.actual_duration_s > 0:
            return self.actual_duration_s
        if self.planned_duration_s is not None and self.planned_duration_s > 0:
            return self.planned_duration_s
        return None


class SonicationTimingService:
    """Resolve per-sonication duration from the workstation summary XML.

    The summary rows are stored in sonication order.  Using the measured
    ``actualduration`` prevents the previous fixed 4-second frame spacing from
    stretching a 3-second cavitation test into a roughly 40-second replay.
    """

    SUMMARY_NAMES = ("SonicationSummary.xml", "sonicationsummary.xml")

    def read_all(self, workspace: Path) -> list[SonicationTiming]:
        summary = self._find_summary(workspace)
        if summary is None:
            return []
        try:
            rows = parse_ado_rowset(summary)
        except (ET.ParseError, OSError, ValueError):
            return []
        result: list[SonicationTiming] = []
        for row in rows:
            if "actualduration" not in row and "duration" not in row:
                continue
            result.append(SonicationTiming(
                planned_duration_s=self._number(row.get("duration")),
                actual_duration_s=self._number(row.get("actualduration")),
                planned_power_w=self._number(row.get("power")),
                source=summary,
            ))
        return result

    def _find_summary(self, workspace: Path) -> Path | None:
        direct = workspace / "SonicationSummary.xml"
        if direct.exists():
            return direct
        candidates = [p for p in workspace.rglob("*.xml") if p.name.lower() == "sonicationsummary.xml"]
        return sorted(candidates, key=lambda p: len(p.parts))[0] if candidates else None

    @staticmethod
    def _number(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value.strip()) if isinstance(value, str) else float(value)
        except (TypeError, ValueError):
            return None
