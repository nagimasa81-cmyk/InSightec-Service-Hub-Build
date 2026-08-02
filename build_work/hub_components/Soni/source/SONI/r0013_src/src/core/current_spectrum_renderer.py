from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt


@dataclass(slots=True)
class CurrentSpectrumRenderResult:
    series: list[tuple[str, np.ndarray, np.ndarray, str]]
    frame_indices: dict[str, int]
    metrics: dict[str, float]


class CurrentSpectrumRenderer:
    """Workstation-style acoustic spectrum renderer with stable normalization.

    Unlike the earlier frame-by-frame normalization, this renderer derives one
    baseline and one scale from the complete selected sonication channel. This
    preserves real energy changes and makes score rises visible in the spectrum.
    """

    X_MIN_MHZ = 0.20
    X_MAX_MHZ = 0.80
    Y_MIN = 0.0
    Y_MAX = 4.0

    @staticmethod
    def _raw_frame(frame) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(frame.frequency, float) / 1_000_000.0
        y = np.abs(np.nan_to_num(np.asarray(frame.amplitude, float), nan=0.0, posinf=0.0, neginf=0.0))
        mask = np.isfinite(x) & np.isfinite(y) & (x >= CurrentSpectrumRenderer.X_MIN_MHZ) & (x <= CurrentSpectrumRenderer.X_MAX_MHZ)
        return x[mask], y[mask]

    @staticmethod
    def _smooth(values: np.ndarray) -> np.ndarray:
        if values.size < 5:
            return values
        kernel = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], float)
        kernel /= kernel.sum()
        return np.convolve(values, kernel, mode="same")

    def _reference(self, frames: list) -> tuple[np.ndarray | None, np.ndarray | None, float]:
        spectra = []
        common_x = None
        for frame in frames:
            x, y = self._raw_frame(frame)
            if not x.size:
                continue
            if common_x is None:
                common_x = x
                spectra.append(y)
            else:
                spectra.append(np.interp(common_x, x, y, left=np.nan, right=np.nan))
        if common_x is None or not spectra:
            return None, None, 1.0
        matrix = np.asarray(spectra, float)
        quiet_count = max(1, min(matrix.shape[0], max(3, int(round(matrix.shape[0] * 0.10)))))
        baseline = np.nanmedian(matrix[:quiet_count], axis=0)
        delta = np.maximum(matrix - baseline[None, :], 0.0)
        scale = float(np.nanpercentile(delta, 99.7))
        if not np.isfinite(scale) or scale <= 1e-30:
            scale = max(float(np.nanmax(delta)) if np.isfinite(delta).any() else 1.0, 1e-30)
        return common_x, baseline, scale

    def _mode_spectrum(self, frames: list, idx: int, mode: str, window: int = 5) -> tuple[np.ndarray, np.ndarray]:
        common_x, baseline, scale = self._reference(frames)
        if common_x is None or baseline is None:
            return np.asarray([]), np.asarray([])
        mode = (mode or "Average").strip().lower()
        lo = max(0, idx - max(1, window) + 1)
        selected = frames[lo:idx + 1] if frames else []
        rows = []
        for frame in selected:
            x, y = self._raw_frame(frame)
            if x.size:
                rows.append(np.interp(common_x, x, y, left=np.nan, right=np.nan))
        if not rows:
            return np.asarray([]), np.asarray([])
        matrix = np.asarray(rows, float)
        if mode.startswith("current"):
            raw = matrix[-1]
            signal = np.maximum(raw - baseline, 0.0)
        elif mode.startswith("max"):
            signal = np.nanmax(np.maximum(matrix - baseline[None, :], 0.0), axis=0)
        elif mode.startswith("baseline"):
            signal = np.maximum(matrix[-1] - baseline, 0.0)
        else:  # Average: default and closest to the score integration window.
            signal = np.nanmean(np.maximum(matrix - baseline[None, :], 0.0), axis=0)
        relative = np.clip(self._smooth(signal / scale * 3.65), 0.0, self.Y_MAX)
        return common_x, relative

    def render(
        self,
        plot,
        channels: dict[str, list],
        selected: list[str],
        frame_index: int,
        replay_count: int,
        colors: dict[str, str],
        main_frequency_hz: float | None,
        map_index: Callable[[int, int, int], int],
        replay_seconds: float,
        title: str = "",
        mode: str = "Average",
        average_window: int = 5,
        frame_indices: dict[str, int] | None = None,
    ) -> CurrentSpectrumRenderResult:
        plot.clear()
        plot.showGrid(x=True, y=True, alpha=.22)
        plot.setLabel("left", "Relative Amplitude")
        plot.setLabel("bottom", "Frequency", units="MHz")
        if title:
            plot.setTitle(title)

        series: list[tuple[str, np.ndarray, np.ndarray, str]] = []
        indices: dict[str, int] = {}
        metrics: dict[str, float] = {}
        active = [ch for ch in selected if channels.get(ch)]
        single = len(active) <= 1
        for ch in active:
            frames = channels[ch]
            if frame_indices is not None and ch in frame_indices:
                idx = min(max(0, int(frame_indices[ch])), len(frames) - 1)
            else:
                idx = map_index(frame_index, replay_count, len(frames))
            indices[ch] = idx
            x, y = self._mode_spectrum(frames, idx, mode, average_window)
            if not x.size:
                continue
            color = "#ff8c1a" if single else colors.get(ch, "#ffffff")
            plot.plot(x, y, pen=pg.mkPen(color, width=2.2), name=ch)
            series.append((ch, x, y, ""))
            if single:
                main_mhz = float(main_frequency_hz or 0.0) / 1_000_000.0
                def band_energy(center: float, half_width: float) -> float:
                    mask = (x >= center-half_width) & (x <= center+half_width)
                    return float(np.trapezoid(y[mask], x[mask])) if mask.sum() > 1 else 0.0
                sub = band_energy(main_mhz/2.0, 0.015) if main_mhz else 0.0
                ultra = band_energy(main_mhz*1.5, 0.015) if main_mhz else 0.0
                exclusions = np.zeros(x.shape, dtype=bool)
                if main_mhz:
                    for center in (main_mhz/2.0, main_mhz, main_mhz*1.5):
                        exclusions |= np.abs(x-center) <= 0.025
                broadband = float(np.trapezoid(y[~exclusions], x[~exclusions])) if (~exclusions).sum() > 1 else 0.0
                total = float(np.trapezoid(y, x)) if x.size > 1 else 0.0
                metrics.update(subharmonic=sub, ultraharmonic=ultra, broadband=broadband, total=total)

        main = float(main_frequency_hz or 0.0) / 1_000_000.0
        for value, label, color in (
            (main / 2.0, "Sub", "#55d7ff"),
            (main * 1.5, "Ultra", "#bf5af2"),
            (main, "Main", "#ffd24a"),
        ):
            if self.X_MIN_MHZ <= value <= self.X_MAX_MHZ:
                plot.addItem(pg.InfiniteLine(
                    pos=value, angle=90, movable=False,
                    pen=pg.mkPen(color, width=1.0, style=Qt.PenStyle.DashLine),
                    label=label,
                ))

        time_text = pg.TextItem(
            text=f"{mode} · Time: {replay_seconds:.2f} s",
            color="#ff8c1a", anchor=(1.0, 0.0),
            fill=pg.mkBrush(20, 20, 20, 130),
        )
        time_text.setPos(self.X_MAX_MHZ - 0.005, self.Y_MAX - 0.08)
        time_text.setZValue(50)
        plot.addItem(time_text)
        plot.setXRange(self.X_MIN_MHZ, self.X_MAX_MHZ, padding=0)
        plot.setYRange(self.Y_MIN, self.Y_MAX, padding=0)
        return CurrentSpectrumRenderResult(series, indices, metrics)
