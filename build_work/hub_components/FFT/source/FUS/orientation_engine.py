"""DICOM orientation engine used by MR Image Explorer.

The engine deliberately keeps patient geometry separate from the viewer's
2-D display transform.  This prevents image labels from drifting when the
rendering backend uses an upward-positive Y axis (as pyqtgraph does).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

import numpy as np


_OPPOSITE = {"L": "R", "R": "L", "A": "P", "P": "A", "H": "F", "F": "H", "S": "I", "I": "S"}


def opposite_label(label: str) -> str:
    return "".join(_OPPOSITE.get(char, "?") for char in str(label or ""))


def patient_axis_label(vector: Any, threshold: float = 0.20) -> str:
    """Return one or two dominant DICOM LPS patient-axis letters."""
    values = np.asarray(vector, dtype=float).reshape(-1)
    if values.size < 3 or not np.all(np.isfinite(values[:3])):
        return "?"
    x, y, z = values[:3]
    candidates = [
        (abs(float(x)), "L" if x >= 0 else "R"),
        (abs(float(y)), "P" if y >= 0 else "A"),
        (abs(float(z)), "H" if z >= 0 else "F"),
    ]
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [label for magnitude, label in candidates if magnitude >= threshold]
    return "".join(selected[:2] or [candidates[0][1]])


@dataclass(frozen=True)
class DisplayTransform:
    rotation_degrees: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    transpose: bool = False
    # pyqtgraph ImageItem is shown in a ViewBox whose Y axis increases upward.
    # With row-major NumPy data, row 0 is therefore at the visual bottom.
    y_axis_up: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "DisplayTransform":
        value = value or {}
        return cls(
            rotation_degrees=int(value.get("rotation_degrees", 0) or 0) % 360,
            flip_horizontal=bool(value.get("flip_horizontal", False)),
            flip_vertical=bool(value.get("flip_vertical", False)),
            transpose=bool(value.get("transpose", False)),
            y_axis_up=bool(value.get("y_axis_up", False)),
        )


@dataclass
class OrientationResult:
    top: str
    bottom: str
    left: str
    right: str
    slice: str
    patient_position: str
    row_vector: list[float]
    column_vector: list[float]
    slice_vector: list[float]
    image_position: list[float] | None
    base_edges: dict[str, str]
    display_transform: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OrientationEngine:
    """PS3.3-compatible DICOM geometry and viewer transform handling."""

    @staticmethod
    def parse_geometry(ds: Any) -> dict[str, Any] | None:
        if ds is None:
            return None
        orientation = getattr(ds, "ImageOrientationPatient", None)
        if orientation is None or len(orientation) < 6:
            return None
        try:
            # DICOM: first triplet is direction of increasing column index
            # (left-to-right on a conventional raster); second is direction
            # of increasing row index (top-to-bottom on a conventional raster).
            row_vector = np.asarray(orientation[:3], dtype=float)
            column_vector = np.asarray(orientation[3:6], dtype=float)
        except Exception:
            return None
        if not np.all(np.isfinite(row_vector)) or not np.all(np.isfinite(column_vector)):
            return None
        row_norm = float(np.linalg.norm(row_vector))
        column_norm = float(np.linalg.norm(column_vector))
        if row_norm <= 1e-8 or column_norm <= 1e-8:
            return None
        row_vector /= row_norm
        column_vector /= column_norm
        slice_vector = np.cross(row_vector, column_vector)
        slice_norm = float(np.linalg.norm(slice_vector))
        if slice_norm > 1e-8:
            slice_vector /= slice_norm
        position = getattr(ds, "ImagePositionPatient", None)
        try:
            image_position = [float(v) for v in position[:3]] if position is not None else None
        except Exception:
            image_position = None
        return {
            "row_vector": row_vector,
            "column_vector": column_vector,
            "slice_vector": slice_vector,
            "image_position": image_position,
            "patient_position": str(getattr(ds, "PatientPosition", "") or "").upper() or "-",
        }

    @staticmethod
    def base_labels(geometry: Mapping[str, Any]) -> dict[str, str]:
        right = patient_axis_label(geometry["row_vector"])
        bottom = patient_axis_label(geometry["column_vector"])
        return {
            "left": opposite_label(right),
            "right": right,
            "top": opposite_label(bottom),
            "bottom": bottom,
        }

    @staticmethod
    def apply_transform(labels: Mapping[str, str], transform: DisplayTransform) -> dict[str, str]:
        result = dict(labels)

        # Convert conventional raster coordinates (row 0 at top) to the actual
        # pyqtgraph display coordinates (row 0 at bottom).
        if transform.y_axis_up:
            result["top"], result["bottom"] = result["bottom"], result["top"]

        if transform.transpose:
            old = dict(result)
            result.update({
                "top": old["left"], "bottom": old["right"],
                "left": old["top"], "right": old["bottom"],
            })

        for _ in range((transform.rotation_degrees // 90) % 4):
            old = dict(result)
            result.update({
                "top": old["left"], "right": old["top"],
                "bottom": old["right"], "left": old["bottom"],
            })

        if transform.flip_horizontal:
            result["left"], result["right"] = result["right"], result["left"]
        if transform.flip_vertical:
            result["top"], result["bottom"] = result["bottom"], result["top"]
        return result

    def calculate(self, ds: Any, transform: Mapping[str, Any] | DisplayTransform | None = None) -> OrientationResult | None:
        geometry = self.parse_geometry(ds)
        if geometry is None:
            return None
        display_transform = transform if isinstance(transform, DisplayTransform) else DisplayTransform.from_mapping(transform)
        base = self.base_labels(geometry)
        final = self.apply_transform(base, display_transform)
        return OrientationResult(
            top=final["top"], bottom=final["bottom"], left=final["left"], right=final["right"],
            slice=patient_axis_label(geometry["slice_vector"]),
            patient_position=geometry["patient_position"],
            row_vector=geometry["row_vector"].tolist(),
            column_vector=geometry["column_vector"].tolist(),
            slice_vector=geometry["slice_vector"].tolist(),
            image_position=geometry["image_position"],
            base_edges=base,
            display_transform=asdict(display_transform),
        )
