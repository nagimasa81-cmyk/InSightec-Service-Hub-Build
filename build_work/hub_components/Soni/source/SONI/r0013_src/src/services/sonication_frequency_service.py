from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SonicationFrequency:
    frequency_hz: float | None
    source: Path | None = None
    raw_line: str | None = None


class SonicationFrequencyService:
    """Resolve the configured transmit/main frequency from a Sonication folder.

    Sonication-local settings are authoritative. ACT and text-like setting files
    are checked before the package-wide Xd_*.ini fallback is used.
    """

    _KEY_RE = re.compile(
        r"(?:main|center|central|transmit|sonication|working|fundamental)?\s*"
        r"(?:frequency|freq)\s*[:=]\s*([-+]?\d+(?:\.\d+)?)\s*(mhz|khz|hz)?",
        re.I,
    )

    def read(self, folder: Path) -> SonicationFrequency:
        candidates = sorted(
            (p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.act','.ini','.cfg','.conf','.txt','.xml'}),
            key=lambda p: (0 if p.suffix.lower()=='.act' else 1, len(p.parts), p.name.lower()),
        )
        for path in candidates:
            try:
                text = path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            for line in text.splitlines():
                match = self._KEY_RE.search(line)
                if not match:
                    continue
                value=float(match.group(1)); unit=(match.group(2) or '').lower()
                if unit=='mhz': hz=value*1_000_000.0
                elif unit=='khz': hz=value*1_000.0
                elif unit=='hz': hz=value
                elif value < 10: hz=value*1_000_000.0
                elif value < 10_000: hz=value*1_000.0
                else: hz=value
                if 10_000 <= hz <= 10_000_000:
                    return SonicationFrequency(hz, path, line.strip())
        return SonicationFrequency(None)
