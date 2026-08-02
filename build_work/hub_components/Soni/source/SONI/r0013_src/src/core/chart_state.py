from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ChartState:
    """Persistent chart interaction state independent from loaded Sonication data."""
    cpc_enabled: bool = False
    selected_channels: set[str] = field(default_factory=set)
    user_selected_channels: bool = False
    x_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    y_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    lut_name: str = "workstation"
    threshold: float | None = None
    spectrum_mode: str = "Average"
    spectrum_average_window: int = 5
    temperature_user_zoomed: bool = False

    def remember_range(self, key: str, x_range, y_range) -> None:
        self.x_ranges[key] = (float(x_range[0]), float(x_range[1]))
        self.y_ranges[key] = (float(y_range[0]), float(y_range[1]))
