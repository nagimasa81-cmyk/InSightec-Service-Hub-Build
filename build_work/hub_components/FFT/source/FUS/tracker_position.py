from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np


@dataclass
class DirectionMeasurement:
    line_index: int
    plane: int
    rotation_deg: float
    peak_bin: float
    coordinate_mm: float
    snr_like: float


def subpixel_peak_bin(magnitude: np.ndarray, index: int) -> float:
    """Parabolic sub-bin interpolation around a spectral maximum."""
    if index <= 0 or index >= len(magnitude) - 1:
        return float(index)
    y1 = float(magnitude[index - 1])
    y2 = float(magnitude[index])
    y3 = float(magnitude[index + 1])
    denominator = y1 - 2.0 * y2 + y3
    if abs(denominator) < 1e-15:
        return float(index)
    delta = 0.5 * (y1 - y3) / denominator
    return float(index) + float(np.clip(delta, -1.0, 1.0))


def signal_peak_coordinate(
    signal: np.ndarray,
    fft_length: int = 1024,
    fov_mm: float = 500.0,
) -> tuple[float, float, float, np.ndarray]:
    """
    Convert a 1D tracker signal peak to a physical coordinate.

    The conversion follows the attached TrackerApp configuration:
      coordinate = (peak_bin - FFT_length / 2) * FOV / FFT_length

    Returns peak_bin, coordinate_mm, an SNR-like peak/background ratio,
    and the shifted magnitude spectrum.
    """
    values = np.asarray(signal).squeeze()
    if values.ndim != 1 or values.size < 4:
        raise ValueError("A 1D tracker signal with at least four samples is required.")
    if fft_length < values.size:
        fft_length = int(2 ** math.ceil(math.log2(values.size)))
    fft_length = max(8, int(fft_length))
    fov_mm = float(fov_mm)
    if not np.isfinite(fov_mm) or fov_mm <= 0:
        raise ValueError("FOV must be a positive finite value.")

    centered = values - np.mean(values)
    spectrum = np.fft.fftshift(np.fft.fft(centered, n=fft_length))
    magnitude = np.abs(spectrum).astype(float)
    peak_index = int(np.argmax(magnitude))
    peak_bin = subpixel_peak_bin(magnitude, peak_index)
    coordinate_mm = (peak_bin - fft_length / 2.0) * fov_mm / fft_length

    background = np.median(magnitude)
    snr_like = float(magnitude[peak_index] / max(background, np.finfo(float).eps))
    return peak_bin, float(coordinate_mm), snr_like, magnitude


def direction_vector(plane: int, rotation_deg: float) -> np.ndarray:
    """
    Create a scanner-coordinate projection direction from plane and
    in-plane rotation.

    Plane mapping follows mapVBVDrunner.py:
      0 = axial/transverse
      1 = coronal
      2 = sagittal

    This is the basic geometric transform. Vendor gradient non-linearity
    correction is intentionally handled by a separate optional adapter.
    """
    theta = math.radians(float(rotation_deg))
    c = math.cos(theta)
    s = math.sin(theta)

    if int(plane) == 0:      # Axial: x-y plane
        vector = np.array([c, s, 0.0], dtype=float)
    elif int(plane) == 1:    # Coronal: x-z plane
        vector = np.array([c, 0.0, s], dtype=float)
    elif int(plane) == 2:    # Sagittal: y-z plane
        vector = np.array([0.0, c, s], dtype=float)
    else:
        raise ValueError(f"Unsupported plane value: {plane}")
    norm = np.linalg.norm(vector)
    return vector / max(norm, np.finfo(float).eps)


def solve_position(
    measurements: Iterable[DirectionMeasurement],
    center_offset: np.ndarray | list[float] | tuple[float, float, float],
    oppose_ap: bool = True,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Solve the 3D tracker position from multiple 1D projection coordinates.

    Returns:
      scanner_xyz_mm, pqr_mm, RMS projection residual
    """
    rows = []
    values = []
    for item in measurements:
        rows.append(direction_vector(item.plane, item.rotation_deg))
        values.append(float(item.coordinate_mm))

    if len(rows) < 3:
        raise ValueError("At least three directional measurements are required.")

    matrix = np.vstack(rows)
    rhs = np.asarray(values, dtype=float)
    relative_xyz, _, rank, _ = np.linalg.lstsq(matrix, rhs, rcond=None)
    if rank < 3:
        raise ValueError("The selected directions do not provide a full 3D solution.")

    offset = np.asarray(center_offset, dtype=float).reshape(3)
    scanner_xyz = relative_xyz + offset

    # PQR is exposed separately so sign conventions remain visible/editable.
    pqr = scanner_xyz.copy()
    if oppose_ap:
        pqr[1] *= -1.0

    residual = matrix @ relative_xyz - rhs
    rms_error = float(np.sqrt(np.mean(residual ** 2)))
    return scanner_xyz, pqr, rms_error
