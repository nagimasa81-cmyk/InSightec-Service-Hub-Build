from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass(slots=True)
class SkullElement:
    number: int
    enabled: bool
    failure_reason: int
    values: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class SkullMeasuresData:
    source: Path | None = None
    elements: list[SkullElement] = field(default_factory=list)
    header: dict[str, str] = field(default_factory=dict)
    error: str = ""


class SkullMeasuresService:
    """Parse the 47-column SkullMeasures_sonic*_cue*.log format."""

    # Zero-based indices, matching the numbered column description embedded in the log.
    PARAMETERS = {
        "Element On/Off": 1,
        "Failure Reason": 2,
        "Phase Correction": 4,
        "Total Phase Shift": 5,
        "Outer Angle": 6,
        "Inner Angle": 7,
        "Skull Thickness": 8,
        "Air in Skull": 9,
        "Average Skull Velocity": 10,
        "Average Shear Velocity": 11,
        "Ray Shift": 12,
        "Critical Angle": 13,
        "Element X": 14,
        "Element Y": 15,
        "Element Z": 16,
        "Element-to-Skull Distance": 41,
        "Skull-to-Focal Distance": 42,
        "First Cortex Intensity": 43,
        "Second Cortex Intensity": 44,
        "Marrow Intensity": 45,
        "Element SDR": 46,
    }

    def find_and_read(self, folder: Path, sonication_number: int | None = None, workspace: Path | None = None) -> SkullMeasuresData:
        roots = [folder]
        if workspace and workspace != folder:
            roots.append(workspace)
        candidates: list[Path] = []
        token = f"sonic{sonication_number}" if sonication_number else ""
        for root in roots:
            if not root or not root.exists():
                continue
            for path in root.rglob("SkullMeasures*.log"):
                if token and token not in path.name.lower():
                    continue
                candidates.append(path)
        candidates = sorted(set(candidates), key=lambda p: (len(p.parts), str(p).lower()))
        return self.read(candidates[0]) if candidates else SkullMeasuresData(error="SkullMeasures log not found")

    def read(self, path: Path) -> SkullMeasuresData:
        result = SkullMeasuresData(source=path)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            result.error = str(exc)
            return result

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("%"):
                body = stripped[1:].strip()
                # Preserve useful header values, including labels with spaces.
                for chunk in re.split(r"\t+|\s{2,}", body):
                    if "=" in chunk:
                        key, value = chunk.split("=", 1)
                        key = key.strip(); value = value.strip()
                        if key and value:
                            result.header[key] = value
                continue
            if not stripped or not stripped[0].isdigit():
                continue
            # Workstation logs sometimes concatenate adjacent signed values
            # (for example ``0.000-135.144``), so whitespace splitting loses
            # columns. Extract numeric tokens directly instead.
            tokens = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", stripped)
            if len(tokens) < 47:
                continue
            try:
                raw = [float(x) for x in tokens[:47]]
            except ValueError:
                continue
            values = {name: raw[index] for name, index in self.PARAMETERS.items()}
            result.elements.append(SkullElement(
                number=int(raw[0]), enabled=int(raw[1]) != 0,
                failure_reason=int(raw[2]), values=values,
            ))
        if not result.elements:
            result.error = "No valid 47-column element rows"
        return result
