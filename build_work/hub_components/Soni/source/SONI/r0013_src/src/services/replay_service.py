from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from src.domain.models import SonicationModel
from src.services.raw_service import RawService

@dataclass(slots=True)
class ReplayFrameData:
    replay_index: int
    magnitude_index: int | None
    temperature_index: int | None
    magnitude: np.ndarray | None
    temperature: np.ndarray | None
    temperature_delta: np.ndarray | None
    hotspot_x: int | None = None
    hotspot_y: int | None = None
    maximum_temperature: float | None = None
    mean_temperature: float | None = None
    maximum_delta_temperature: float | None = None
    mean_delta_temperature: float | None = None
    temperature_source: str = "Unavailable"
    reference_temperature: float | None = None
    roi_source: str = "Default center ROI"
    roi_center_x: float | None = None
    roi_center_y: float | None = None
    roi_radius: float | None = None
    roi_width: float | None = None
    roi_height: float | None = None

class ReplayService:
    """Decode thermometry into workstation-style absolute-temperature data.

    The RAW format is inferred conservatively:
    * plausible 15..100 C values => absolute temperature
    * values centered near zero => delta-temperature, converted with a 37 C
      reference until an ACT/protocol-derived reference becomes available.
    """
    def __init__(self):
        self.raw = RawService()
        self._baseline_cache: dict[str, np.ndarray] = {}
        self._mode_cache: dict[str, tuple[str, float]] = {}

    def _baseline(self, son: SonicationModel) -> np.ndarray | None:
        if not son.temperature_frames:
            return None
        key = str(son.folder.resolve())
        if key not in self._baseline_cache:
            self._baseline_cache[key] = self.raw.read_temperature(son.temperature_frames[0].path)
        return self._baseline_cache[key]

    def _temperature_mode(self, son: SonicationModel) -> tuple[str, float]:
        key = str(son.folder.resolve())
        if key in self._mode_cache:
            return self._mode_cache[key]
        baseline = self._baseline(son)
        if baseline is None:
            result = ("Unavailable", 37.0)
        else:
            finite = baseline[np.isfinite(baseline)]
            if not finite.size:
                result = ("Unavailable", 37.0)
            else:
                median = float(np.nanmedian(finite))
                p01, p99 = np.nanpercentile(finite, [1, 99])
                # FUS workstation thermometry typically starts around body temp.
                if 15.0 <= median <= 80.0 and -10.0 <= p01 and p99 <= 120.0:
                    result = ("Absolute RAW", median)
                else:
                    result = ("Delta RAW + 37.0 C reference", 37.0)
        self._mode_cache[key] = result
        return result

    def clear_cache(self) -> None:
        self._baseline_cache.clear()
        self._mode_cache.clear()

    @staticmethod
    def _roi_geometry(shape: tuple[int, int]) -> tuple[float, float, float, float]:
        """Return the requested target-centred 3 x 3 pixel voxel.

        This ROI is deliberately expressed in pixels.  It does not pretend that
        pixel spacing has been decoded from the export metadata.
        """
        h, w = shape
        # Use a real pixel centre, not a half-pixel coordinate on even matrices.
        # This guarantees that the inclusive mask contains exactly 3 x 3 pixels.
        cy, cx = float(h // 2), float(w // 2)
        return cx, cy, 3.0, 3.0

    @classmethod
    def _roi_mask(cls, shape: tuple[int, int]) -> np.ndarray:
        h, w = shape
        cx, cy, width, height = cls._roi_geometry(shape)
        yy, xx = np.ogrid[:h, :w]
        half_w=max((width-1.0)/2.0,0.0); half_h=max((height-1.0)/2.0,0.0)
        return (np.abs(xx-cx)<=half_w) & (np.abs(yy-cy)<=half_h)

    def frame(self, son: SonicationModel, index: int) -> ReplayFrameData:
        count = son.replay_frame_count
        index = max(0, min(index, count - 1))
        mag = raw_temp = abs_temp = delta = None
        mi = ti = None
        source, reference_temp = self._temperature_mode(son)
        baseline = self._baseline(son)

        if son.magnitude_frames:
            mi = self.raw.normalize_index(index, count, len(son.magnitude_frames))
            mag = self.raw.read_magnitude(son.magnitude_frames[mi].path)
        if son.temperature_frames:
            ti = self.raw.normalize_index(index, count, len(son.temperature_frames))
            raw_temp = self.raw.read_temperature(son.temperature_frames[ti].path)
            if source == "Absolute RAW":
                abs_temp = raw_temp
                if baseline is not None and baseline.shape == raw_temp.shape:
                    delta = raw_temp - baseline
            else:
                # A delta RAW is already relative to the scanner reference.
                delta = raw_temp
                abs_temp = raw_temp + reference_temp

        hx = hy = None
        mx = mean = md = meand = None
        if abs_temp is not None and np.isfinite(abs_temp).any():
            roi = self._roi_mask(abs_temp.shape)
            roi_values = np.where(roi, abs_temp, np.nan)
            safe = np.nan_to_num(roi_values, nan=-np.inf)
            flat = int(np.argmax(safe))
            hy, hx = np.unravel_index(flat, abs_temp.shape)
            mx = float(np.nanmax(roi_values))
            mean = float(np.nanmean(roi_values))
        if delta is not None and np.isfinite(delta).any():
            roi = self._roi_mask(delta.shape)
            roi_delta = np.where(roi, delta, np.nan)
            md = float(np.nanmax(roi_delta))
            meand = float(np.nanmean(roi_delta))

        roi_x = roi_y = roi_radius = roi_width = roi_height = None
        roi_shape = abs_temp.shape if abs_temp is not None else (delta.shape if delta is not None else None)
        if roi_shape is not None:
            roi_x, roi_y, roi_width, roi_height = self._roi_geometry(roi_shape)
            roi_radius = max(roi_width, roi_height) / 2.0

        return ReplayFrameData(
            index, mi, ti, mag, abs_temp, delta, hx, hy, mx, mean, md, meand,
            source, reference_temp, "Target center voxel, 3 x 3 pixels (20-pixel target circle is display only)",
            roi_x, roi_y, roi_radius, roi_width, roi_height
        )
