from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from .hybrid_compensation import compensate, detect_artifacts, ifft2c


@dataclass(frozen=True)
class AutoCorrectResult:
    kspace: np.ndarray
    image: np.ndarray
    mask: np.ndarray
    metrics: dict[str, float]
    candidates: list[dict[str, Any]]
    selected_types: list[str]


def _gradient_energy(image: np.ndarray) -> float:
    a = np.asarray(image, dtype=float)
    gy = np.diff(a, axis=0, append=a[-1:, :])
    gx = np.diff(a, axis=1, append=a[:, -1:])
    return float(np.mean(np.hypot(gx, gy)))


def _quality(before_k: np.ndarray, result, mask: np.ndarray, protection: float) -> dict[str, float]:
    before_img = np.abs(ifft2c(before_k))
    after_img = np.asarray(result.image, dtype=float)
    eps = 1e-12
    roi_before = np.abs(before_k)[mask]
    roi_after = np.abs(result.kspace)[mask]
    artifact_reduction = float(np.clip(1.0 - np.mean(roi_after) / max(np.mean(roi_before), eps), -1.0, 1.0)) if np.any(mask) else 0.0
    image_delta = float(np.mean(np.abs(after_img - before_img)) / max(np.mean(np.abs(before_img)), eps))
    edge_before = _gradient_energy(before_img)
    edge_after = _gradient_energy(after_img)
    detail_preservation = float(np.clip(1.0 - abs(edge_after - edge_before) / max(edge_before, eps), 0.0, 1.0))
    outside_change = image_delta
    residual = float(np.clip(np.mean(roi_after) / max(np.mean(roi_before), eps), 0.0, 2.0)) if np.any(mask) else 1.0
    overall = 100.0 * (0.58 * max(artifact_reduction, 0.0) + 0.30 * detail_preservation + 0.12 * (1.0 - min(outside_change, 1.0)))
    overall -= 100.0 * float(protection) * max(0.0, outside_change - 0.035)
    mask_coverage = float(np.count_nonzero(mask)) / float(mask.size) if mask.size else 0.0
    edge_preservation = detail_preservation
    return {
        "artifact_reduction": 100.0 * artifact_reduction,
        "detail_preservation": 100.0 * detail_preservation,
        "edge_preservation": 100.0 * edge_preservation,
        "outside_image_change": 100.0 * outside_change,
        "residual_artifact": 100.0 * residual,
        "mask_coverage": 100.0 * mask_coverage,
        "overall_quality": float(overall),
    }




def _bright_blob_mask(kspace: np.ndarray, removal_f: float, protect_f: float) -> np.ndarray:
    """Detect broad, soft or edge-clipped off-centre FFT blobs.

    Commit0114 extends the detector for the real-world pattern reported by the
    user: several rounded bright regions touching the left/right FFT borders.
    Detection combines robust global intensity, multi-scale local contrast,
    edge-band statistics, non-wrapping region growth and mirrored-pair support.
    The protected DC centre is always removed from the final mask.
    """
    mag = np.abs(np.asarray(kspace, dtype=np.complex128)).astype(float)
    if mag.ndim != 2:
        return np.zeros_like(mag, dtype=bool)
    h, w = mag.shape
    yy, xx = np.ogrid[:h, :w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0

    centre_r = max(4.0, min(h, w) * (0.030 + 0.042 * protect_f))
    dc_guard = ((yy - cy) ** 2 + (xx - cx) ** 2) < centre_r ** 2
    finite_mask = np.isfinite(mag)
    valid = finite_mask & ~dc_guard
    vals = mag[valid]
    if vals.size < 32:
        return np.zeros_like(mag, dtype=bool)

    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)))
    sigma = max(1.4826 * mad, max(abs(med), 1.0) * 1e-12)

    def box_blur(a: np.ndarray, radius: int) -> np.ndarray:
        radius = max(1, int(radius))
        pad = np.pad(a, ((radius, radius), (radius, radius)), mode="reflect")
        integ = np.pad(pad, ((1, 0), (1, 0)), mode="constant").cumsum(0).cumsum(1)
        k = 2 * radius + 1
        return (integ[k:, k:] - integ[:-k, k:] - integ[k:, :-k] + integ[:-k, :-k]) / float(k * k)

    # Multi-scale background.  The larger radius is important for rounded blobs
    # tens of pixels wide; reflect padding alone is not trusted at the border,
    # so a dedicated edge statistic is also used below.
    radii = (2, max(4, int(round(min(h, w) * 0.018))), max(7, int(round(min(h, w) * 0.040))))
    backgrounds = [box_blur(mag, r) for r in radii]
    contrast = np.maximum.reduce([mag - bg for bg in backgrounds])
    cvals = contrast[valid]
    cmed = float(np.median(cvals))
    cmad = float(np.median(np.abs(cvals - cmed)))
    csig = max(1.4826 * cmad, sigma * 0.02, 1e-12)

    # Global seeds remain conservative for normal high-energy encoding signal.
    pct = float(np.clip(99.60 - 0.95 * removal_f + 0.18 * protect_f, 98.45, 99.75))
    global_thr = max(
        float(np.percentile(vals, pct)),
        med + (3.15 + 1.55 * protect_f - 1.55 * removal_f) * sigma,
    )
    local_thr = cmed + (2.25 + 1.35 * protect_f - 1.35 * removal_f) * csig
    global_seed = valid & (mag >= global_thr)
    local_seed = valid & (contrast >= local_thr) & (mag >= med + (1.35 + 0.55 * protect_f) * sigma)

    # Edge-aware seeds.  Cropped blobs can lose local contrast because reflected
    # padding mirrors the bright signal.  Compare them against the edge-band's
    # own robust distribution and allow a lower seed threshold there.
    edge_width = max(5, int(round(min(h, w) * (0.055 + 0.035 * removal_f))))
    edge_band = (
        (xx < edge_width) | (xx >= w - edge_width) |
        (yy < edge_width) | (yy >= h - edge_width)
    ) & valid
    edge_vals = mag[edge_band]
    edge_seed = np.zeros_like(valid, dtype=bool)
    if edge_vals.size >= 16:
        emed = float(np.median(edge_vals))
        emad = float(np.median(np.abs(edge_vals - emed)))
        esig = max(1.4826 * emad, sigma * 0.25, 1e-12)
        epct = float(np.clip(98.85 - 1.10 * removal_f + 0.22 * protect_f, 96.8, 99.35))
        edge_thr = max(
            float(np.percentile(edge_vals, epct)),
            emed + (2.15 + 1.20 * protect_f - 1.15 * removal_f) * esig,
            med + (1.45 + 0.45 * protect_f) * sigma,
        )
        edge_seed = edge_band & (mag >= edge_thr)
        # Soft edge blobs may have only moderate absolute intensity but a broad
        # positive contrast at the middle/large scale.
        edge_seed |= edge_band & (contrast >= cmed + (1.55 + 0.95 * protect_f - 0.95 * removal_f) * csig) & (mag >= med + 1.15 * sigma)

    seeds = global_seed | local_seed | edge_seed

    def shifted(src: np.ndarray, dy: int, dx: int) -> np.ndarray:
        """Shift without np.roll wrap-around, avoiding false left/right bridges."""
        out = np.zeros_like(src, dtype=bool)
        ys = slice(max(0, dy), min(h, h + dy))
        xs = slice(max(0, dx), min(w, w + dx))
        sy = slice(max(0, -dy), min(h, h - dy))
        sx = slice(max(0, -dx), min(w, w - dx))
        out[ys, xs] = src[sy, sx]
        return out

    # Grow from strong seeds into the full soft blob.  Edge pixels receive a
    # slightly lower floor because the observed blobs are truncated by display/
    # acquisition borders.
    grow_thr = max(med + 0.95 * sigma, global_thr * (0.34 + 0.15 * protect_f))
    edge_grow_thr = max(med + 0.80 * sigma, grow_thr * 0.78)
    grown = seeds.copy()
    iterations = 6 + int(round(5 * removal_f))
    for _ in range(iterations):
        count = np.zeros_like(mag, dtype=np.uint8)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                count += shifted(grown, dy, dx).astype(np.uint8)
        intensity_ok = (mag >= grow_thr) | (edge_band & (mag >= edge_grow_thr))
        contrast_ok = contrast >= cmed + (0.55 + 0.45 * protect_f) * csig
        nxt = valid & (count >= 1) & intensity_ok & (contrast_ok | (count >= 3))
        merged = grown | nxt
        if np.array_equal(merged, grown):
            break
        grown = merged

    # One close-like pass joins small holes/gaps inside broad rounded regions.
    neighbor_count = np.zeros_like(mag, dtype=np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            neighbor_count += shifted(grown, dy, dx).astype(np.uint8)
    grown |= valid & (neighbor_count >= 5) & (mag >= med + 0.65 * sigma)

    # Label components and preserve plausible clipped edge blobs.  Mirrored
    # left/right or top/bottom partners receive additional support, matching the
    # common Hermitian artifact pattern visible in the supplied image.
    seen = np.zeros_like(grown, dtype=bool)
    components: list[dict[str, Any]] = []
    for y in range(h):
        for x in range(w):
            if not grown[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            pts: list[tuple[int, int]] = []
            while stack:
                py, px = stack.pop()
                pts.append((py, px))
                for ny in range(max(0, py - 1), min(h, py + 2)):
                    for nx in range(max(0, px - 1), min(w, px + 2)):
                        if grown[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            ys = np.fromiter((q[0] for q in pts), dtype=int)
            xs = np.fromiter((q[1] for q in pts), dtype=int)
            area = int(len(pts))
            bh = int(ys.max() - ys.min() + 1)
            bw = int(xs.max() - xs.min() + 1)
            fill = area / max(1, bh * bw)
            edge_touch = bool(ys.min() == 0 or ys.max() == h - 1 or xs.min() == 0 or xs.max() == w - 1)
            mean_c = float(np.mean(contrast[ys, xs])) / csig
            peak_z = float((np.max(mag[ys, xs]) - med) / sigma)
            components.append({
                "ys": ys, "xs": xs, "area": area, "fill": fill,
                "edge_touch": edge_touch, "mean_c": mean_c, "peak_z": peak_z,
                "cy": float(np.mean(ys)), "cx": float(np.mean(xs)),
                "height": bh, "width": bw,
            })

    min_area = max(4, int(round(min(h, w) * 0.010)))
    max_area = max(min_area + 1, int(round(grown.size * (0.018 + 0.085 * removal_f))))

    # Determine approximate Hermitian partners around the FFT centre.
    pair_tol = max(5.0, min(h, w) * 0.065)
    for i, comp in enumerate(components):
        target_y = 2.0 * cy - comp["cy"]
        target_x = 2.0 * cx - comp["cx"]
        comp["paired"] = any(
            j != i and np.hypot(other["cy"] - target_y, other["cx"] - target_x) <= pair_tol
            for j, other in enumerate(components)
        )

    out = np.zeros_like(grown, dtype=bool)
    for comp in components:
        area = comp["area"]
        if not (min_area <= area <= max_area):
            continue
        min_fill = 0.035 if comp["edge_touch"] else 0.055
        contrast_req = 0.75 + 0.70 * protect_f
        if comp["paired"]:
            contrast_req -= 0.22
        if comp["edge_touch"]:
            contrast_req -= 0.20
        broad_enough = max(comp["height"], comp["width"]) >= 3
        intensity_ok = comp["peak_z"] >= (2.0 + 0.8 * protect_f - 0.7 * removal_f)
        if broad_enough and comp["fill"] >= min_fill and comp["mean_c"] >= contrast_req and intensity_ok:
            out[comp["ys"], comp["xs"]] = True

    # Never permit the DC protection area back into the result.
    out[dc_guard] = False
    return out

def auto_correct(
    kspace: np.ndarray,
    *,
    threshold_sigma: float = 3.0,
    sensitivity: str = "Conservative",
    removal: int = 50,
    detail: int = 70,
    protection: int = 80,
    target_ratio: float = 1.0,
) -> AutoCorrectResult:
    """Candidate-by-candidate virtual reconstruction and quality selection.

    Detection is intentionally broad, but candidates are accepted only when a
    trial reconstruction improves artifact energy without excessive image change.
    """
    source = np.asarray(kspace)
    if source.ndim != 2:
        raise ValueError("Auto Correct requires a 2-D k-space array.")
    removal_f = float(np.clip(removal / 100.0, 0.0, 1.0))
    detail_f = float(np.clip(detail / 100.0, 0.0, 1.0))
    protect_f = float(np.clip(protection / 100.0, 0.0, 1.0))
    level = "Low" if removal < 30 else "Mid" if removal < 58 else "High" if removal < 85 else "Extreme"
    structure_preservation = float(np.clip(0.35 + 0.60 * max(detail_f, protect_f), 0.35, 0.97))
    magnitude = np.abs(source).astype(float)
    finite = magnitude[np.isfinite(magnitude)]
    if finite.size:
        median = float(np.median(finite))
        mad = float(np.median(np.abs(finite - median)))
        robust_sigma = max(1.4826 * mad, 1e-12)
        tail_ratio = float(np.percentile(finite, 99.5) / max(median + robust_sigma, 1e-12))
    else:
        tail_ratio = 1.0
    adaptive_offset = float(np.clip(0.35 * np.log10(max(tail_ratio, 1.0)), 0.0, 1.0))
    threshold = float(threshold_sigma + 0.8 * protect_f - 0.55 * removal_f - adaptive_offset)

    trials: list[dict[str, Any]] = []
    accepted_masks: list[np.ndarray] = []
    accepted_types: list[str] = []
    current = source.copy()
    type_order = ("Spike", "Blob", "Block", "Diagonal", "Line", "Band", "Ring")
    minimum_gain = 18.0 + 16.0 * protect_f - 10.0 * removal_f

    for artifact_type in type_order:
        if artifact_type == "Blob":
            mask = _bright_blob_mask(source, removal_f, protect_f)
            confidence = float(np.clip(np.count_nonzero(mask) / max(mask.size * 0.002, 1.0), 0.0, 1.0))
            compensation_type = "Block"
        else:
            detection = detect_artifacts(source, artifact_type, threshold, sensitivity)
            mask = np.asarray(detection.mask, dtype=bool)
            confidence = detection.confidence
            compensation_type = artifact_type
        if not np.any(mask):
            continue
        coverage = float(np.count_nonzero(mask)) / float(mask.size)
        # Large line/band proposals are especially likely to be normal encoding signal.
        if artifact_type in {"Line", "Band", "Ring"} and coverage > (0.012 + 0.030 * removal_f):
            trials.append({"type": artifact_type, "accepted": False, "reason": "coverage_guard", "coverage": coverage, "quality_gain": -999.0, "mask": mask.copy()})
            continue
        try:
            trial = compensate(
                current, mask,
                artifact_type=compensation_type,
                level=level,
                threshold_sigma=threshold,
                target_ratio=target_ratio,
                adaptive_direction=True,
                frequency_aware=True,
                harmonic_poisson=True,
                multi_pass=True,
                hermitian_symmetry=True,
                mask_expansion=0 if protect_f >= 0.65 else 1,
                donor_halo=3 if protect_f >= 0.65 else 4,
                pass_count=1 if protect_f >= 0.75 else 2,
                strength_override=float(np.clip(0.35 + 0.55 * removal_f, 0.35, 0.90)),
                structure_preservation=structure_preservation,
                detection_sensitivity=sensitivity,
            )
            q = _quality(current, trial, mask, protect_f)
            gain = q["overall_quality"]
            if artifact_type == "Blob":
                # Broad edge blobs are visually obvious but can produce a more
                # modest global quality gain.  Accept plausible, compact Blob
                # masks with strong confidence under a still-bounded image-change
                # guard rather than forcing the stricter line/band criterion.
                blob_min_gain = max(7.0, minimum_gain - 9.0)
                blob_change_limit = 14.0 - 6.0 * protect_f
                accepted = bool(
                    gain >= blob_min_gain
                    and q["artifact_reduction"] > 2.0
                    and q["outside_image_change"] <= blob_change_limit
                    and coverage <= (0.025 + 0.070 * removal_f)
                )
            else:
                accepted = bool(gain >= minimum_gain and q["artifact_reduction"] > 4.0 and q["outside_image_change"] <= (12.0 - 7.0 * protect_f))
            shape_bonus = 1.0 if artifact_type in {"Spike", "Blob", "Diagonal"} else 0.85
            candidate_score = float(np.clip(0.45 * gain + 35.0 * confidence + 20.0 * shape_bonus - 150.0 * coverage, -999.0, 100.0))
            record = {"type": artifact_type, "accepted": accepted, "coverage": coverage, "confidence": confidence, "quality_gain": gain, "candidate_score": candidate_score, "adaptive_threshold": threshold, "mask": mask.copy(), **q}
            if not accepted:
                reasons = []
                active_min_gain = max(7.0, minimum_gain - 9.0) if artifact_type == "Blob" else minimum_gain
                active_reduction = 2.0 if artifact_type == "Blob" else 4.0
                active_change_limit = (14.0 - 6.0 * protect_f) if artifact_type == "Blob" else (12.0 - 7.0 * protect_f)
                if gain < active_min_gain: reasons.append("quality_below_threshold")
                if q["artifact_reduction"] <= active_reduction: reasons.append("artifact_reduction_too_small")
                if q["outside_image_change"] > active_change_limit: reasons.append("image_change_too_large")
                record["reason"] = ", ".join(reasons) or "validation_rejected"
            trials.append(record)
            if accepted:
                current = trial.kspace
                accepted_masks.append(mask)
                accepted_types.append(artifact_type)
        except Exception as exc:
            trials.append({"type": artifact_type, "accepted": False, "reason": str(exc), "coverage": coverage, "quality_gain": -999.0, "mask": mask.copy()})

    if accepted_masks:
        final_mask = np.logical_or.reduce(accepted_masks)
    else:
        final_mask = np.zeros(source.shape, dtype=bool)
    final_image = np.abs(ifft2c(current))
    if np.any(final_mask):
        class R: pass
        r = R(); r.kspace = current; r.image = final_image
        metrics = _quality(source, r, final_mask, protect_f)
    else:
        metrics = {"artifact_reduction": 0.0, "detail_preservation": 100.0, "outside_image_change": 0.0, "residual_artifact": 100.0, "overall_quality": 0.0}
    metrics["accepted_candidates"] = float(len(accepted_types))
    metrics["mask_pixels"] = float(np.count_nonzero(final_mask))
    return AutoCorrectResult(current, final_image, final_mask, metrics, trials, accepted_types)


def recalculate_with_mask(
    kspace: np.ndarray,
    mask: np.ndarray,
    *,
    artifact_type: str = "Auto",
    threshold_sigma: float = 3.0,
    sensitivity: str = "Conservative",
    removal: int = 50,
    detail: int = 75,
    protection: int = 85,
    target_ratio: float = 1.0,
) -> AutoCorrectResult:
    """Reconstruct exactly once from the current mask and Quick Adjust values.

    This path never performs candidate selection or Auto Retry.  The supplied
    mask remains authoritative and is returned unchanged.
    """
    source = np.asarray(kspace)
    active_mask = np.asarray(mask, dtype=bool)
    if source.ndim != 2:
        raise ValueError("Quick Adjust requires a 2-D k-space array.")
    if active_mask.shape != source.shape or not np.any(active_mask):
        raise ValueError("The current compensation mask is empty or has an invalid shape.")

    removal_f = float(np.clip(removal / 100.0, 0.0, 1.0))
    detail_f = float(np.clip(detail / 100.0, 0.0, 1.0))
    protect_f = float(np.clip(protection / 100.0, 0.0, 1.0))
    level = "Low" if removal < 30 else "Mid" if removal < 58 else "High" if removal < 85 else "Extreme"
    structure_preservation = float(np.clip(0.35 + 0.60 * max(detail_f, protect_f), 0.35, 0.97))
    threshold = float(threshold_sigma + 0.8 * protect_f - 0.55 * removal_f)

    result = compensate(
        source, active_mask, artifact_type=artifact_type, level=level,
        threshold_sigma=threshold, target_ratio=target_ratio,
        adaptive_direction=False, frequency_aware=True, harmonic_poisson=True,
        multi_pass=True, hermitian_symmetry=True,
        mask_expansion=0 if protect_f >= 0.65 else 1,
        donor_halo=3 if protect_f >= 0.65 else 4,
        pass_count=1 if protect_f >= 0.75 else 2,
        strength_override=float(np.clip(0.35 + 0.55 * removal_f, 0.35, 0.90)),
        structure_preservation=structure_preservation,
        detection_sensitivity=sensitivity,
    )
    metrics = _quality(source, result, active_mask, protect_f)
    metrics["accepted_candidates"] = 1.0
    metrics["mask_pixels"] = float(np.count_nonzero(active_mask))
    return AutoCorrectResult(
        result.kspace, np.asarray(result.image), active_mask.copy(), metrics,
        [{"type": "Current Mask", "accepted": True, "source": "quick_adjust_once"}],
        ["Current Mask"],
    )


AUTO_RETRY_TRIALS: tuple[dict[str, int], ...] = (
    {"removal": 50, "detail": 75, "protection": 85},
    {"removal": 60, "detail": 75, "protection": 75},
    {"removal": 70, "detail": 75, "protection": 65},
    {"removal": 80, "detail": 75, "protection": 55},
    {"removal": 90, "detail": 75, "protection": 45},
    {"removal": 100, "detail": 75, "protection": 35},
)


def _result_rank(result: AutoCorrectResult) -> tuple[float, float, float, float, float]:
    """Rank quality first, then safer image change/residual/detail tie breakers."""
    m = result.metrics
    return (
        float(m.get("overall_quality", 0.0)),
        -float(m.get("outside_image_change", 100.0)),
        -float(m.get("residual_artifact", 100.0)),
        float(m.get("detail_preservation", 0.0)),
        float(m.get("artifact_reduction", 0.0)),
    )


def auto_correct_with_retry(
    kspace: np.ndarray,
    *,
    threshold_sigma: float = 3.0,
    sensitivity: str = "Conservative",
    target_ratio: float = 1.0,
    quality_threshold: float = 60.0,
    progress_callback=None,
    cancel_callback=None,
) -> tuple[AutoCorrectResult, list[dict[str, Any]]]:
    """Run six Quick Adjust trials and return the best validated result.

    The underlying candidate detection, validation, virtual compensation, and
    quality engine remain unchanged. This function only orchestrates retries.
    """
    source = np.asarray(kspace)
    trial_log: list[dict[str, Any]] = []
    results: list[AutoCorrectResult] = []
    for index, settings in enumerate(AUTO_RETRY_TRIALS, start=1):
        if cancel_callback is not None and cancel_callback():
            break
        if progress_callback is not None:
            progress_callback(index, len(AUTO_RETRY_TRIALS), "searching", settings, None)
        result = auto_correct(
            source,
            threshold_sigma=threshold_sigma,
            sensitivity=sensitivity,
            removal=settings["removal"],
            detail=settings["detail"],
            protection=settings["protection"],
            target_ratio=target_ratio,
        )
        results.append(result)
        candidate_found = bool(result.selected_types and np.any(result.mask))
        quality = float(result.metrics.get("overall_quality", 0.0))
        reliable = bool(candidate_found and quality >= quality_threshold)
        record = {
            "trial": index,
            **settings,
            "candidate_found": candidate_found,
            "quality": quality,
            "reliable": reliable,
            "selected_types": list(result.selected_types),
        }
        trial_log.append(record)
        if progress_callback is not None:
            progress_callback(index, len(AUTO_RETRY_TRIALS), "evaluating", settings, record)
    if not results:
        empty = auto_correct(
            source, threshold_sigma=threshold_sigma, sensitivity=sensitivity,
            removal=50, detail=75, protection=85, target_ratio=target_ratio,
        )
        return empty, trial_log
    reliable_results = [r for r, log in zip(results, trial_log) if log["reliable"]]
    candidate_results = [r for r, log in zip(results, trial_log) if log["candidate_found"]]
    pool = reliable_results or candidate_results or results
    return max(pool, key=_result_rank), trial_log
