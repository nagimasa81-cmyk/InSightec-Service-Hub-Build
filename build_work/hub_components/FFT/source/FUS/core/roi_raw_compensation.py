from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RoiCompensationDetection:
    mask: np.ndarray
    replacement: np.ndarray
    background: float
    sigma: float
    mode: str
    stats: dict[str, Any]


def _robust_sigma(values: np.ndarray, floor: float = 1e-12) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    median = float(np.median(values)) if values.size else 0.0
    mad = float(np.median(np.abs(values - median))) if values.size else 0.0
    return median, max(1.4826 * mad, abs(median) * 0.02, floor)


def _shift_no_wrap(array: np.ndarray, dy: int, dx: int, fill_value=0) -> np.ndarray:
    """Shift a 2-D array without wrapping opposite edges together."""
    source = np.asarray(array)
    result = np.full(source.shape, fill_value, dtype=source.dtype)
    rows, cols = source.shape
    src_y0, src_y1 = max(0, -dy), min(rows, rows - dy)
    src_x0, src_x1 = max(0, -dx), min(cols, cols - dx)
    if src_y0 >= src_y1 or src_x0 >= src_x1:
        return result
    dst_y0, dst_y1 = src_y0 + dy, src_y1 + dy
    dst_x0, dst_x1 = src_x0 + dx, src_x1 + dx
    result[dst_y0:dst_y1, dst_x0:dst_x1] = source[src_y0:src_y1, src_x0:src_x1]
    return result


def _dilate(mask: np.ndarray, radius_y: int = 1, radius_x: int = 1) -> np.ndarray:
    result = np.asarray(mask, dtype=bool).copy()
    source = result.copy()
    for dy in range(-max(0, radius_y), max(0, radius_y) + 1):
        for dx in range(-max(0, radius_x), max(0, radius_x) + 1):
            if dy == 0 and dx == 0:
                continue
            result |= _shift_no_wrap(source, dy, dx, False)
    return result


def _validate(raw_data: np.ndarray) -> np.ndarray:
    source = np.asarray(raw_data)
    if source.ndim != 2:
        raise ValueError("ROI RAW compensation requires a 2-D k-space array.")
    if min(source.shape) < 3:
        raise ValueError("ROI RAW compensation requires at least a 3 x 3 array.")
    if not np.all(np.isfinite(source)):
        raise ValueError("ROI RAW compensation cannot process NaN or infinite samples.")
    if np.issubdtype(source.dtype, np.integer):
        source = source.astype(np.float64)
    return source


def _bounds(shape: tuple[int, int], y0: int, y1: int, x0: int, x1: int) -> tuple[int, int, int, int]:
    rows, cols = shape
    y0 = max(1, min(int(y0), rows - 2))
    y1 = max(y0 + 1, min(int(y1), rows - 1))
    x0 = max(1, min(int(x0), cols - 2))
    x1 = max(x0 + 1, min(int(x1), cols - 1))
    return y0, y1, x0, x1


def detect_roi_artifact_mask(
    raw_data: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    *,
    mode: str = "Line",
    threshold_sigma: float = 3.0,
    target_ratio: float = 1.0,
) -> RoiCompensationDetection:
    """Detect a structured artifact inside a user-selected RAW ROI.

    This detector is intentionally separate from spike-noise detection. It does
    not search the complete dataset for isolated hot pixels. It only creates a
    mask inside the operator-selected ROI for line, band, block, or ring-like
    high-signal structures and estimates a background replacement surface from
    the ROI boundary.
    """
    source = _validate(raw_data)
    y0, y1, x0, x1 = _bounds(source.shape, y0, y1, x0, x1)
    threshold_sigma = float(np.clip(threshold_sigma, 1.0, 12.0))
    target_ratio = float(np.clip(target_ratio, 0.25, 3.0))

    rows, cols = source.shape
    cy, cx = rows // 2, cols // 2
    h, w = y1 - y0, x1 - x0
    roi = source[y0:y1, x0:x1]
    roi_mag = np.abs(roi)
    eps = 1e-12

    margin = max(4, int(min(rows, cols) * 0.02))
    ya, yb = max(0, y0 - margin), min(rows, y1 + margin)
    xa, xb = max(0, x0 - margin), min(cols, x1 + margin)
    neighborhood = source[ya:yb, xa:xb]
    ring = np.ones(neighborhood.shape, dtype=bool)
    ring[y0 - ya:y1 - ya, x0 - xa:x1 - xa] = False
    gy, gx = np.indices(neighborhood.shape)
    gy += ya
    gx += xa
    guard = max(2, int(min(rows, cols) * 0.012))
    ring &= ~((np.abs(gy - cy) <= guard) | (np.abs(gx - cx) <= guard))
    ring_mag = np.abs(neighborhood[ring])
    if ring_mag.size < 12:
        empty = np.zeros((h, w), dtype=bool)
        return RoiCompensationDetection(empty, roi.copy(), 0.0, 0.0, mode, {"changed": 0})

    background, sigma = _robust_sigma(ring_mag)

    top = source[y0 - 1, x0:x1]
    bottom = source[y1, x0:x1]
    left = source[y0:y1, x0 - 1]
    right = source[y0:y1, x1]
    ty = np.linspace(0.0, 1.0, h)[:, None]
    tx = np.linspace(0.0, 1.0, w)[None, :]
    vertical = (1.0 - ty) * top[None, :] + ty * bottom[None, :]
    horizontal = (1.0 - tx) * left[:, None] + tx * right[:, None]
    surface = 0.5 * (vertical + horizontal)
    surface_mag = np.clip(np.abs(surface), background * 0.35, background + 1.5 * sigma)
    replacement = surface_mag * target_ratio * np.exp(1j * np.angle(surface + eps))
    if not np.iscomplexobj(source):
        replacement = np.real(replacement)

    limit = background + threshold_sigma * sigma
    high = roi_mag > limit
    normalized = str(mode).strip().lower()

    row_fraction = np.mean(high, axis=1)
    col_fraction = np.mean(high, axis=0)
    row_energy = np.percentile(roi_mag / np.maximum(np.abs(replacement), eps), 85, axis=1)
    col_energy = np.percentile(roi_mag / np.maximum(np.abs(replacement), eps), 85, axis=0)

    if normalized == "line":
        rows_sel = (row_fraction >= max(0.18, 3.0 / max(w, 1))) | (row_energy > 1.45)
        cols_sel = (col_fraction >= max(0.18, 3.0 / max(h, 1))) | (col_energy > 1.45)
        mask = (rows_sel[:, None] | cols_sel[None, :]) & high
        mask = _dilate(mask, 0, 1) | _dilate(mask, 1, 0)
    elif normalized == "band":
        rows_sel = row_fraction >= max(0.30, 4.0 / max(w, 1))
        cols_sel = col_fraction >= max(0.30, 4.0 / max(h, 1))
        mask = (rows_sel[:, None] | cols_sel[None, :]) & (roi_mag > background + 1.5 * sigma)
        mask = _dilate(mask, 1, 1)
    elif normalized == "block":
        mask = _dilate(high, 1, 1)
        support = sum(np.roll(np.roll(high, dy, 0), dx, 1)
                      for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        mask &= support >= 3
    elif normalized == "ring":
        yy, xx = np.indices((h, w), dtype=float)
        rr = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
        bins = np.clip(rr.astype(int), 0, max(h, w))
        sums = np.bincount(bins.ravel(), weights=roi_mag.ravel())
        counts = np.bincount(bins.ravel())
        radial = sums / np.maximum(counts, 1)
        radial_med, radial_sigma = _robust_sigma(radial[counts > 0])
        selected_bins = radial > radial_med + max(1.5, threshold_sigma * 0.6) * radial_sigma
        mask = high & selected_bins[bins]
        mask = _dilate(mask, 1, 1)
    else:
        raise ValueError(f"Unsupported ROI RAW compensation mode: {mode}")

    global_y, global_x = np.indices((h, w))
    global_y += y0
    global_x += x0
    mask &= ~((np.abs(global_y - cy) <= guard) | (np.abs(global_x - cx) <= guard))

    stats = {
        "changed": int(np.count_nonzero(mask)),
        "background": float(background),
        "sigma": float(sigma),
        "before_max": float(np.max(roi_mag)) if roi_mag.size else 0.0,
        "mode": mode,
    }
    return RoiCompensationDetection(mask, replacement, background, sigma, mode, stats)




def _inpaint_complex_from_unmasked(source: np.ndarray, full_mask: np.ndarray, max_iter: int = 512) -> np.ndarray:
    """Fill painted samples from neighbouring unmasked k-space values.

    Unlike bounding-box interpolation, this follows the actual painted shape and
    therefore works for thin lines, curved regions, and disconnected brush marks.
    """
    src = np.asarray(source)
    mask = np.asarray(full_mask, dtype=bool)
    filled = src.astype(np.complex128 if np.iscomplexobj(src) else np.float64, copy=True)
    known = ~mask
    pending = mask.copy()
    for _ in range(max_iter):
        if not np.any(pending):
            break
        total = np.zeros_like(filled)
        count = np.zeros(mask.shape, dtype=np.int16)
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
            vals = _shift_no_wrap(filled, dy, dx, 0)
            oks = _shift_no_wrap(known, dy, dx, False)
            total += np.where(oks, vals, 0)
            count += oks.astype(np.int16)
        ready = pending & (count > 0)
        if not np.any(ready):
            break
        filled[ready] = total[ready] / count[ready]
        known[ready] = True
        pending[ready] = False
    if np.any(pending):
        fallback = np.median(src[~mask]) if np.any(~mask) else 0.0
        filled[pending] = fallback
    return filled

def build_manual_mask_detection(
    raw_data: np.ndarray,
    mask: np.ndarray,
    *,
    target_ratio: float = 1.0,
    mask_expand: int = 0,
    donor_halo: int = 1,
    model_passes: int = 1,
    stripe_suppression: float = 0.0,
    edge_blend: bool = False,
) -> tuple[RoiCompensationDetection, tuple[int, int, int, int]]:
    """Build replacement values from the actual operator-painted shape."""
    source = _validate(raw_data)
    painted_mask = np.asarray(mask, dtype=bool)
    if painted_mask.shape != source.shape:
        raise ValueError("Manual RAW mask must match the k-space dimensions.")
    mask_expand = int(np.clip(mask_expand, 0, 8))
    donor_halo = int(np.clip(donor_halo, 1, 12))
    model_passes = int(np.clip(model_passes, 1, 3))
    stripe_suppression = float(np.clip(stripe_suppression, 0.0, 1.0))
    edge_blend = bool(edge_blend)
    full_mask = _dilate(painted_mask, mask_expand, mask_expand) if mask_expand else painted_mask.copy()
    ys, xs = np.where(full_mask)
    if ys.size == 0:
        raise ValueError("Paint at least one RAW-data pixel before Preview.")
    # Manual painting is allowed up to the true k-space border.  Keep a one-pixel
    # context where available, but do not discard painted edge pixels.
    y0, y1 = max(0, int(ys.min()) - 1), min(source.shape[0], int(ys.max()) + 2)
    x0, x1 = max(0, int(xs.min()) - 1), min(source.shape[1], int(xs.max()) + 2)
    roi_mask = full_mask[y0:y1, x0:x1].copy()

    # Exclude a one-pixel halo from donor samples. This prevents a painted
    # artifact core from being reconstructed from the same artifact immediately
    # outside the brush stroke, while still applying changes only to painted pixels.
    donor_exclusion = _dilate(full_mask, donor_halo, donor_halo)

    # Formal Background Model: reconstruct masked k-space from uncontaminated
    # surrounding samples, then refine it for up to three passes. Each pass uses
    # the previous model as the starting field while the donor halo remains
    # excluded, preventing stripe/band energy adjacent to the brush from leaking
    # back into the replacement surface.
    background_model = _inpaint_complex_from_unmasked(source, donor_exclusion)
    for _ in range(1, model_passes):
        seeded = source.copy()
        seeded[donor_exclusion] = background_model[donor_exclusion]
        background_model = _inpaint_complex_from_unmasked(seeded, donor_exclusion)

    if stripe_suppression > 0.0:
        # Build robust row/column background trends from donor pixels. Combining
        # both axes aggressively rejects coherent horizontal/vertical RAW bands.
        valid = ~donor_exclusion
        row_model = np.empty_like(background_model)
        col_model = np.empty_like(background_model)
        global_fallback = np.median(source[valid]) if np.any(valid) else 0.0
        for row in range(source.shape[0]):
            vals = source[row, valid[row]]
            row_model[row, :] = np.median(vals) if vals.size else global_fallback
        for col in range(source.shape[1]):
            vals = source[valid[:, col], col]
            col_model[:, col] = np.median(vals) if vals.size else global_fallback
        structured_model = 0.5 * (row_model + col_model)
        # Clamp axis models to the robust global donor envelope. A stripe that
        # spans an entire row/column must not become its own background model.
        donor_mag = np.abs(source[valid])
        donor_level, donor_sigma = _robust_sigma(donor_mag)
        max_mag = donor_level + 2.0 * donor_sigma
        structured_mag = np.minimum(np.abs(structured_model), max_mag)
        structured_phase = np.exp(1j * np.angle(structured_model + 1e-12))
        structured_model = structured_mag * structured_phase
        if not np.iscomplexobj(source):
            structured_model = np.real(structured_model)
        global_model = np.full_like(background_model, global_fallback)
        structured_model = 0.35 * structured_model + 0.65 * global_model
        background_model[full_mask] = (
            background_model[full_mask] * (1.0 - stripe_suppression)
            + structured_model[full_mask] * stripe_suppression
        )

    replacement = background_model[y0:y1, x0:x1].copy()
    target_ratio = float(np.clip(target_ratio, 0.0, 3.0))
    replacement *= target_ratio

    # Background statistics come from a narrow ring around the real painted mask.
    outer = _dilate(full_mask, 3, 3) & ~full_mask
    ring_values = np.abs(source[outer])
    if ring_values.size < 8:
        ring_values = np.abs(source[~full_mask])
    background, sigma = _robust_sigma(ring_values)
    before = np.abs(source[y0:y1, x0:x1])[roi_mask]
    after = np.abs(replacement)[roi_mask]
    stats = {
        "changed": int(np.count_nonzero(roi_mask)),
        "background": float(background),
        "sigma": float(sigma),
        "before_max": float(np.max(before)) if before.size else 0.0,
        "replacement_max": float(np.max(after)) if after.size else 0.0,
        "before_mean_mask": float(np.mean(before)) if before.size else 0.0,
        "replacement_mean_mask": float(np.mean(after)) if after.size else 0.0,
        "mode": "Manual Paint",
        "painted_pixels": int(np.count_nonzero(painted_mask)),
        "mask_expand": mask_expand,
        "donor_halo": donor_halo,
        "background_model": True,
        "model_passes": model_passes,
        "stripe_suppression": stripe_suppression,
        "edge_blend": edge_blend,
    }
    return RoiCompensationDetection(roi_mask, replacement, background, sigma, "Manual Paint", stats), (y0, y1, x0, x1)


def apply_roi_background_compensation(
    raw_data: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    detection: RoiCompensationDetection,
    *,
    strength: float = 1.0,
    return_stats: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    source = _validate(raw_data)
    if str(detection.mode).lower() == "manual paint":
        rows, cols = source.shape
        y0, y1 = max(0, min(int(y0), rows - 1)), max(1, min(int(y1), rows))
        x0, x1 = max(0, min(int(x0), cols - 1)), max(1, min(int(x1), cols))
        if y1 <= y0 or x1 <= x0:
            raise ValueError("Manual RAW compensation bounds are empty.")
    else:
        y0, y1, x0, x1 = _bounds(source.shape, y0, y1, x0, x1)
    result = source.copy()
    roi = source[y0:y1, x0:x1].copy()
    if detection.mask.shape != roi.shape or detection.replacement.shape != roi.shape:
        raise ValueError("Detected ROI mask no longer matches the active ROI.")

    mask = np.asarray(detection.mask, dtype=bool)
    blend = float(np.clip(strength, 0.0, 1.0))
    h, w = roi.shape
    if str(detection.mode).lower() == "manual paint":
        if bool(detection.stats.get("edge_blend", False)):
            # High keeps a minimum 95% background replacement at the boundary
            # and reaches 100% in the interior, avoiding a hard visible seam.
            neighbours = np.zeros((h, w), dtype=np.int16)
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                neighbours += _shift_no_wrap(mask, dy, dx, False).astype(np.int16)
            interior = np.clip(neighbours / 8.0, 0.0, 1.0)
            alpha = blend * (0.95 + 0.05 * interior)
        else:
            alpha = np.full((h, w), blend, dtype=float)
    else:
        fy = np.sin(np.pi * (np.arange(h) + 0.5) / h)[:, None]
        fx = np.sin(np.pi * (np.arange(w) + 0.5) / w)[None, :]
        alpha = blend * np.clip(fy * fx, 0.20, 1.0)
    corrected = roi.copy()
    corrected[mask] = roi[mask] * (1.0 - alpha[mask]) + detection.replacement[mask] * alpha[mask]
    result[y0:y1, x0:x1] = corrected

    rows, cols = result.shape
    cy, cx = rows // 2, cols // 2
    ys, xs = np.where(mask)
    values = result[ys + y0, xs + x0].copy()
    for ly, lx, value in zip(ys, xs, values):
        y, x = ly + y0, lx + x0
        sy, sx = (2 * cy - y) % rows, (2 * cx - x) % cols
        result[sy, sx] = np.conj(value) if np.iscomplexobj(result) else value

    after_mag = np.abs(result[y0:y1, x0:x1])
    stats = dict(detection.stats)
    stats.update({
        "after_max": float(np.max(after_mag)) if after_mag.size else 0.0,
        "before_mean": float(np.mean(np.abs(roi)[mask])) if np.any(mask) else 0.0,
        "after_mean": float(np.mean(after_mag[mask])) if np.any(mask) else 0.0,
        "max_abs_delta": float(np.max(np.abs(corrected[mask] - roi[mask]))) if np.any(mask) else 0.0,
    })
    return (result, stats) if return_stats else result
