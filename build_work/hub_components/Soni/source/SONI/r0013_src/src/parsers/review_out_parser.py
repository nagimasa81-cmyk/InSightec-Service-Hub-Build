from __future__ import annotations
import re
from pathlib import Path

def parse(path: str | Path) -> dict[str, str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    result: dict[str, str] = {}
    patterns = {
        "coil": r"(?im)^\s*coil(?: name)?\s*[:=]\s*(.+)$",
        "protocol": r"(?im)^\s*protocol(?: name)?\s*[:=]\s*(.+)$",
        "series_description": r"(?im)^\s*series(?: description)?\s*[:=]\s*(.+)$",
        "tr": r"(?im)^\s*tr\s*[:=]\s*(.+)$",
        "te": r"(?im)^\s*te\s*[:=]\s*(.+)$",
        "fov": r"(?im)^\s*fov\s*[:=]\s*(.+)$",
        "slice_thickness": r"(?im)^\s*slice thickness\s*[:=]\s*(.+)$",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[key] = match.group(1).strip()
    result["bytes"] = str(len(text.encode("utf-8", errors="ignore")))
    return result
