from __future__ import annotations

"""Viewer display-state model independent from image loading."""

from dataclasses import dataclass, replace
from typing import Any, Optional


@dataclass
class DisplayState:
    mode: str = "Both"
    original_window_level: Optional[tuple[float, float]] = None
    raw_window_level: Optional[tuple[float, float]] = None
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    rotation: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    slice_index: int = 0

    def normalized(self) -> "DisplayState":
        mode = self.mode if self.mode in {"Original", "FFT", "Both"} else "Both"
        rotation = int(self.rotation) % 360
        return replace(self, mode=mode, zoom=max(float(self.zoom), 0.01), rotation=rotation)

    @classmethod
    def capture(cls, window: Any) -> "DisplayState":
        return cls(
            mode=getattr(window, "view_mode", "Both"),
            original_window_level=getattr(window, "original_window_level", None),
            raw_window_level=getattr(window, "raw_window_level", None),
            slice_index=int(getattr(window, "slice_index", 0)),
        ).normalized()

    def apply_layout(self, window: Any) -> None:
        state = self.normalized()
        if hasattr(window, "set_view_mode"):
            window.set_view_mode(state.mode)
        else:
            window.view_mode = state.mode
