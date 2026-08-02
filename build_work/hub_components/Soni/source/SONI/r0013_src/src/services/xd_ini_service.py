from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MainFrequencyMetadata:
    frequency_hz: float | None
    source_path: Path | None
    raw_line: str | None
    confidence: float
    unit_interpretation: str


class XdIniService:
    NUMBER_RE = re.compile(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    )

    def discover(self, workspace: Path) -> list[Path]:
        candidates = []
        for path in workspace.rglob("*.ini"):
            low = path.name.lower()
            if low.startswith("xd_") or low.startswith("xd"):
                candidates.append(path)
        candidates.sort(key=lambda p: str(p).lower())
        return candidates

    def read_main_frequency(self, workspace: Path) -> MainFrequencyMetadata:
        files = self.discover(workspace)
        if not files:
            return MainFrequencyMetadata(
                frequency_hz=None,
                source_path=None,
                raw_line=None,
                confidence=0.0,
                unit_interpretation="Xd INI not found",
            )

        best: MainFrequencyMetadata | None = None
        for path in files:
            metadata = self._parse_file(path)
            if metadata.frequency_hz is not None:
                if best is None or metadata.confidence > best.confidence:
                    best = metadata

        if best is not None:
            return best

        return MainFrequencyMetadata(
            frequency_hz=None,
            source_path=files[-1],
            raw_line=None,
            confidence=10.0,
            unit_interpretation="No numeric value found on final data line",
        )

    def _parse_file(self, path: Path) -> MainFrequencyMetadata:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
            and not line.lstrip().startswith(("#", ";", "//"))
        ]
        if not lines:
            return MainFrequencyMetadata(
                None, path, None, 5.0, "Empty INI"
            )

        raw_line = lines[-1]
        numbers = self.NUMBER_RE.findall(raw_line)
        if not numbers:
            return MainFrequencyMetadata(
                None, path, raw_line, 10.0, "No numeric token"
            )

        value = float(numbers[-1])
        lower = raw_line.lower()

        if "mhz" in lower:
            frequency_hz = value * 1_000_000.0
            interpretation = "Explicit MHz"
            confidence = 100.0
        elif "khz" in lower:
            frequency_hz = value * 1_000.0
            interpretation = "Explicit kHz"
            confidence = 100.0
        elif re.search(r"(?<![kKmM])\bhz\b", raw_line, re.IGNORECASE):
            frequency_hz = value
            interpretation = "Explicit Hz"
            confidence = 100.0
        elif abs(value) < 10.0:
            frequency_hz = value * 1_000_000.0
            interpretation = "Unit inferred as MHz"
            confidence = 80.0
        elif abs(value) < 10_000.0:
            frequency_hz = value * 1_000.0
            interpretation = "Unit inferred as kHz"
            confidence = 75.0
        else:
            frequency_hz = value
            interpretation = "Unit inferred as Hz"
            confidence = 75.0

        if not (10_000.0 <= frequency_hz <= 10_000_000.0):
            confidence = min(confidence, 45.0)
            interpretation += " (outside expected ultrasound range)"

        return MainFrequencyMetadata(
            frequency_hz=frequency_hz,
            source_path=path,
            raw_line=raw_line,
            confidence=confidence,
            unit_interpretation=interpretation,
        )
