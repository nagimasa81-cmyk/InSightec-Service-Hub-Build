"""Legacy Commit0085a compatibility engine.

The active ROI RAW workflow uses ``core.roi_raw_compensation``. This module is
kept only for historical regression tests and is not connected to Spike Diag
or the Commit0085b user interface.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _box_blur_2d(array: np.ndarray, radius: int) -> np.ndarray:
    """NumPy-only box blur with edge padding."""
    source = np.asarray(array, dtype=float)
    radius = max(0, int(radius))
    if radius == 0 or source.size == 0:
        return source.copy()
    kernel = 2 * radius + 1
    padded = np.pad(source, ((radius, radius), (radius, radius)), mode="edge")
    integral = np.pad(padded, ((1, 0), (1, 0)), mode="constant").cumsum(0).cumsum(1)
    return (
        integral[kernel:, kernel:]
        - integral[:-kernel, kernel:]
        - integral[kernel:, :-kernel]
        + integral[:-kernel, :-kernel]
    ) / float(kernel * kernel)


def compensate_roi_to_background(
    raw_data: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    strength: float = 1.0,
    mode: str = "Hybrid (Spikes + Lines)",
    threshold_sigma: float = 3.0,
    target_ratio: float = 1.0,
    return_stats: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Flatten strong ROI signals toward the surrounding background level.

    The routine handles isolated k-space spikes and line-shaped high signals.
    It estimates a complex background surface from the four ROI borders,
    detects excessive magnitude with robust statistics, and reduces only the
    excess while preserving phase and conjugate symmetry. The central DC cross
    is protected from automatic replacement.
    """
    source = np.asarray(raw_data)
    if source.ndim != 2:
        raise ValueError("RAW compensation requires a 2-D k-space array.")
    if source.shape[0] < 3 or source.shape[1] < 3:
        raise ValueError("RAW compensation requires at least a 3 x 3 k-space array.")
    if not np.all(np.isfinite(source)):
        raise ValueError("RAW compensation cannot process NaN or infinite samples.")

    # Integer arrays cannot represent a weighted compensation result. Promote
    # them instead of silently truncating corrected samples on assignment.
    if np.issubdtype(source.dtype, np.integer):
        source = source.astype(np.float64)
    result = source.copy()
    rows, cols = source.shape
    y0 = max(1, min(int(y0), rows - 2))
    y1 = max(y0 + 1, min(int(y1), rows - 1))
    x0 = max(1, min(int(x0), cols - 2))
    x1 = max(x0 + 1, min(int(x1), cols - 1))
    h, w = y1 - y0, x1 - x0
    cy, cx = rows // 2, cols // 2
    blend = float(np.clip(strength, 0.0, 1.0))
    threshold_sigma = float(np.clip(threshold_sigma, 1.0, 12.0))
    target_ratio = float(np.clip(target_ratio, 0.25, 3.0))

    roi = source[y0:y1, x0:x1].copy()
    roi_mag = np.abs(roi)
    eps = max(float(np.finfo(float).eps), 1e-12)

    margin = max(4, int(min(rows, cols) * 0.02))
    ya, yb = max(0, y0 - margin), min(rows, y1 + margin)
    xa, xb = max(0, x0 - margin), min(cols, x1 + margin)
    neighborhood = source[ya:yb, xa:xb]
    ring_mask = np.ones(neighborhood.shape, dtype=bool)
    ring_mask[y0 - ya:y1 - ya, x0 - xa:x1 - xa] = False
    gy, gx = np.indices(neighborhood.shape)
    gy += ya
    gx += xa
    guard = max(2, int(min(rows, cols) * 0.012))
    ring_mask &= ~((np.abs(gy - cy) <= guard) | (np.abs(gx - cx) <= guard))
    ring_mag = np.abs(neighborhood[ring_mask])
    if ring_mag.size < 12:
        stats = {"changed": 0, "line_rows": 0, "line_cols": 0, "background": 0.0}
        return (result, stats) if return_stats else result

    background = float(np.median(ring_mag))
    ring_mad = float(np.median(np.abs(ring_mag - background)))
    ring_sigma = max(1.4826 * ring_mad, background * 0.02, eps)

    top = source[max(0, y0 - 1), x0:x1]
    bottom = source[min(rows - 1, y1), x0:x1]
    left = source[y0:y1, max(0, x0 - 1)]
    right = source[y0:y1, min(cols - 1, x1)]
    ty = np.linspace(0.0, 1.0, h)[:, None]
    tx = np.linspace(0.0, 1.0, w)[None, :]
    vertical = (1.0 - ty) * top[None, :] + ty * bottom[None, :]
    horizontal = (1.0 - tx) * left[:, None] + tx * right[:, None]
    complex_estimate = 0.5 * (vertical + horizontal)

    estimate_mag = np.abs(complex_estimate)
    robust_target = np.minimum(estimate_mag, background + 1.5 * ring_sigma)
    robust_target = np.maximum(robust_target, background * 0.35)
    target_mag = robust_target * target_ratio
    estimate_phase = np.exp(1j * np.angle(complex_estimate + eps))
    replacement = target_mag * estimate_phase
    if not np.iscomplexobj(source):
        replacement = np.real(replacement)

    log_mag = np.log1p(roi_mag)
    blur_radius = max(1, int(round(min(h, w) * 0.05)))
    local_bg = _box_blur_2d(log_mag, blur_radius)
    residual = log_mag - local_bg
    residual_med = float(np.median(residual))
    residual_mad = float(np.median(np.abs(residual - residual_med)))
    residual_sigma = max(1.4826 * residual_mad, eps)
    magnitude_limit = background + threshold_sigma * ring_sigma
    pixel_mask = (roi_mag > magnitude_limit) & (
        residual > residual_med + max(1.75, threshold_sigma * 0.70) * residual_sigma
    )

    excess_ratio = roi_mag / np.maximum(target_mag, eps)
    row_score = np.percentile(excess_ratio, 85.0, axis=1)
    col_score = np.percentile(excess_ratio, 85.0, axis=0)

    def robust_line_mask(score: np.ndarray) -> np.ndarray:
        med = float(np.median(score))
        mad = float(np.median(np.abs(score - med)))
        sigma = max(1.4826 * mad, 0.05)
        return score > max(1.35, med + threshold_sigma * 0.55 * sigma)

    row_lines = robust_line_mask(row_score)
    col_lines = robust_line_mask(col_score)
    line_mask = row_lines[:, None] | col_lines[None, :]
    line_mask &= roi_mag > (target_mag + max(1.25, threshold_sigma * 0.35) * ring_sigma)

    normalized_mode = str(mode).lower()
    if "line" in normalized_mode and "hybrid" not in normalized_mode:
        candidate = line_mask
    elif "strong" in normalized_mode:
        candidate = pixel_mask
    else:
        candidate = pixel_mask | line_mask

    ry, rx = np.indices((h, w))
    global_y, global_x = ry + y0, rx + x0
    candidate &= ~(
        (np.abs(global_y - cy) <= guard)
        | (np.abs(global_x - cx) <= guard)
    )

    if not np.any(candidate):
        stats = {
            "changed": 0,
            "line_rows": int(np.count_nonzero(row_lines)),
            "line_cols": int(np.count_nonzero(col_lines)),
            "background": background,
            "before_max": float(np.max(roi_mag)) if roi_mag.size else 0.0,
            "after_max": float(np.max(roi_mag)) if roi_mag.size else 0.0,
        }
        return (result, stats) if return_stats else result

    fy = np.sin(np.pi * (np.arange(h) + 0.5) / h)[:, None]
    fx = np.sin(np.pi * (np.arange(w) + 0.5) / w)[None, :]
    feather = np.clip(fy * fx, 0.20, 1.0)
    # Confidence depends on the original excess, not on the selected target.
    # This keeps Target background monotonic and predictable for the operator.
    excess = np.maximum(roi_mag - background, 0.0)
    confidence = np.clip(
        excess / max(background * 3.0, ring_sigma * 3.0, eps),
        0.0,
        1.0,
    )
    alpha = blend * feather * np.maximum(confidence, 0.35)

    corrected = roi.copy()
    corrected[candidate] = (
        roi[candidate] * (1.0 - alpha[candidate])
        + replacement[candidate] * alpha[candidate]
    )
    result[y0:y1, x0:x1] = corrected

    ys, xs = np.where(candidate)
    # Take a stable snapshot before writing symmetric partners. This avoids
    # order-dependent results when both members of a conjugate pair are selected.
    changed_values = result[ys + y0, xs + x0].copy()
    for local_y, local_x, changed_value in zip(ys, xs, changed_values):
        y, x = local_y + y0, local_x + x0
        sy, sx = (2 * cy - y) % rows, (2 * cx - x) % cols
        if np.iscomplexobj(result):
            result[sy, sx] = np.conj(changed_value)
        else:
            result[sy, sx] = changed_value

    after_mag = np.abs(result[y0:y1, x0:x1])
    stats = {
        "changed": int(np.count_nonzero(candidate)),
        "line_rows": int(np.count_nonzero(row_lines)),
        "line_cols": int(np.count_nonzero(col_lines)),
        "background": background,
        "before_max": float(np.max(roi_mag)) if roi_mag.size else 0.0,
        "after_max": float(np.max(after_mag)) if after_mag.size else 0.0,
        "before_mean": float(np.mean(roi_mag)) if roi_mag.size else 0.0,
        "after_mean": float(np.mean(after_mag)) if after_mag.size else 0.0,
    }
    return (result, stats) if return_stats else result
