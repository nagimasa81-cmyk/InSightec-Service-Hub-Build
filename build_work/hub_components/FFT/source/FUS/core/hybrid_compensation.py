from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass(frozen=True)
class ArtifactMaskResult:
    mask: np.ndarray
    artifact_type: str
    confidence: float
    direction: str
    stats: dict[str, Any]


@dataclass(frozen=True)
class CompensationResult:
    kspace: np.ndarray
    image: np.ndarray
    difference_fft: np.ndarray
    difference_phase: np.ndarray
    difference_image: np.ndarray
    mask: np.ndarray
    metrics: dict[str, float]
    metadata: dict[str, Any]


def fft2c(image: np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image)))


def ifft2c(kspace: np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace)))


def robust_stats(values: np.ndarray) -> tuple[float, float]:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return 0.0, 1e-12
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    return med, max(1.4826 * mad, abs(med) * 0.01, 1e-12)


def shift_no_wrap(a: np.ndarray, dy: int, dx: int, fill=0) -> np.ndarray:
    src = np.asarray(a)
    out = np.full(src.shape, fill, dtype=src.dtype)
    h, w = src.shape
    sy0, sy1 = max(0, -dy), min(h, h - dy)
    sx0, sx1 = max(0, -dx), min(w, w - dx)
    if sy0 < sy1 and sx0 < sx1:
        out[sy0+dy:sy1+dy, sx0+dx:sx1+dx] = src[sy0:sy1, sx0:sx1]
    return out


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    source = np.asarray(mask, dtype=bool)
    out = source.copy()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            out |= shift_no_wrap(source, dy, dx, False)
    return out


def _laplacian4(values: np.ndarray) -> np.ndarray:
    """Return a no-wrap 4-neighbour discrete Laplacian."""
    a = np.asarray(values)
    up = shift_no_wrap(a, 1, 0)
    down = shift_no_wrap(a, -1, 0)
    left = shift_no_wrap(a, 0, 1)
    right = shift_no_wrap(a, 0, -1)
    degree = np.full(a.shape, 4.0, dtype=float)
    degree[0, :] -= 1.0
    degree[-1, :] -= 1.0
    degree[:, 0] -= 1.0
    degree[:, -1] -= 1.0
    return up + down + left + right - degree * a


def _poisson_fill(
    source: np.ndarray,
    mask: np.ndarray,
    *,
    guidance: np.ndarray | None = None,
    iterations: int = 600,
    omega: float = 1.65,
    tolerance: float = 1e-7,
) -> tuple[np.ndarray, dict[str, float]]:
    """Solve a Dirichlet Poisson inpainting problem inside ``mask``.

    The known samples outside the mask remain fixed.  When ``guidance`` is
    supplied, its discrete Laplacian is used as the Poisson right-hand side;
    otherwise this becomes a harmonic (zero-source) solve.  Complex k-space is
    solved directly because the stencil is linear for real and imaginary parts.
    """
    dtype = np.complex128 if np.iscomplexobj(source) else np.float64
    result = np.asarray(source).astype(dtype, copy=True)
    m = np.asarray(mask, dtype=bool)
    if not np.any(m):
        return result, {"iterations": 0.0, "residual": 0.0, "converged": 1.0}

    known = ~m
    fallback = np.median(result[known]) if np.any(known) else dtype(0.0)
    guide = np.zeros_like(result) if guidance is None else np.asarray(guidance, dtype=dtype)
    if guide.shape != result.shape:
        raise ValueError("Poisson guidance shape must match k-space shape.")
    rhs = _laplacian4(guide)
    result[m] = guide[m] if guidance is not None else fallback

    degree = np.full(result.shape, 4.0, dtype=float)
    degree[0, :] -= 1.0
    degree[-1, :] -= 1.0
    degree[:, 0] -= 1.0
    degree[:, -1] -= 1.0
    yy, xx = np.indices(result.shape)
    parity = (yy + xx) & 1
    omega = float(np.clip(omega, 1.0, 1.95))
    residual = float("inf")
    completed = 0

    # Red-black SOR is deterministic, boundary-safe, and considerably faster
    # than a full Jacobi copy for the larger RAW matrices used by the GUI.
    for iteration in range(max(1, int(iterations))):
        previous = result[m].copy()
        for colour in (0, 1):
            active = m & (parity == colour)
            if not np.any(active):
                continue
            neighbour_sum = (
                shift_no_wrap(result, 1, 0)
                + shift_no_wrap(result, -1, 0)
                + shift_no_wrap(result, 0, 1)
                + shift_no_wrap(result, 0, -1)
            )
            target = (neighbour_sum - rhs) / degree
            result[active] = (1.0 - omega) * result[active] + omega * target[active]
        completed = iteration + 1
        residual = float(np.max(np.abs(result[m] - previous)))
        if residual <= tolerance:
            break

    return result, {
        "iterations": float(completed),
        "residual": residual,
        "converged": float(residual <= tolerance),
    }


def _harmonic_fill(source: np.ndarray, mask: np.ndarray, iterations: int = 160) -> np.ndarray:
    """Compatibility wrapper retained for existing Commit0085-0088 tests."""
    solved, _ = _poisson_fill(source, mask, iterations=iterations, omega=1.0)
    return solved


def enforce_hermitian(kspace: np.ndarray, protected_mask: np.ndarray | None = None) -> np.ndarray:
    result = np.asarray(kspace).copy()
    rows, cols = result.shape
    cy, cx = rows // 2, cols // 2
    mask = np.ones(result.shape, dtype=bool) if protected_mask is None else np.asarray(protected_mask, dtype=bool)
    ys, xs = np.where(mask)
    values = result[ys, xs].copy()
    for y, x, value in zip(ys, xs, values):
        sy, sx = (2 * cy - y) % rows, (2 * cx - x) % cols
        avg = 0.5 * (value + np.conj(result[sy, sx]))
        result[y, x] = avg
        result[sy, sx] = np.conj(avg)
    return result


def _connected_filter(mask: np.ndarray, minimum_size: int = 2) -> np.ndarray:
    """Remove isolated candidate islands without scipy dependencies."""
    source = np.asarray(mask, dtype=bool)
    if not np.any(source):
        return source.copy()
    h, w = source.shape
    seen = np.zeros_like(source, dtype=bool)
    output = np.zeros_like(source, dtype=bool)
    for y0, x0 in zip(*np.where(source & ~seen)):
        if seen[y0, x0]:
            continue
        stack = [(int(y0), int(x0))]
        seen[y0, x0] = True
        component = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and source[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) >= max(1, int(minimum_size)):
            ys, xs = zip(*component)
            output[np.asarray(ys), np.asarray(xs)] = True
    return output


def _mirror_mask_hermitian(mask: np.ndarray) -> np.ndarray:
    source = np.asarray(mask, dtype=bool)
    rows, cols = source.shape
    cy, cx = rows // 2, cols // 2
    ys, xs = np.where(source)
    mirrored = source.copy()
    mirrored[(2 * cy - ys) % rows, (2 * cx - xs) % cols] = True
    return mirrored


def _candidate_confidence(mask: np.ndarray, excess: np.ndarray, coherence: float = 1.0) -> float:
    count = int(np.count_nonzero(mask))
    if count == 0:
        return 0.0
    coverage = count / max(float(mask.size), 1.0)
    mean_excess = float(np.mean(excess[mask])) if np.any(mask) else 0.0
    strength = 1.0 - np.exp(-max(mean_excess, 0.0) / 2.0)
    support = min(1.0, np.sqrt(coverage / 0.0025))
    return float(np.clip(0.55 * strength + 0.30 * support + 0.15 * coherence, 0.0, 1.0))


def _box_mean(values: np.ndarray, radius: int) -> np.ndarray:
    """Small dependency-free local mean with no wraparound."""
    src = np.asarray(values, dtype=float)
    total = np.zeros_like(src, dtype=float)
    count = np.zeros_like(src, dtype=float)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            shifted = shift_no_wrap(src, dy, dx, 0.0)
            valid = shift_no_wrap(np.ones(src.shape, dtype=float), dy, dx, 0.0)
            total += shifted
            count += valid
    return total / np.maximum(count, 1.0)


def _component_records(mask: np.ndarray, score_map: np.ndarray) -> list[dict[str, Any]]:
    """Return 8-connected component geometry and score measurements."""
    source = np.asarray(mask, dtype=bool)
    score = np.asarray(score_map, dtype=float)
    h, w = source.shape
    seen = np.zeros_like(source, dtype=bool)
    records: list[dict[str, Any]] = []
    for y0, x0 in zip(*np.where(source)):
        if seen[y0, x0]:
            continue
        stack = [(int(y0), int(x0))]
        seen[y0, x0] = True
        points: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for dy, dx in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and source[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        ys = np.asarray([p[0] for p in points], dtype=int)
        xs = np.asarray([p[1] for p in points], dtype=int)
        y0b, y1b = int(ys.min()), int(ys.max())
        x0b, x1b = int(xs.min()), int(xs.max())
        bh, bw = y1b-y0b+1, x1b-x0b+1
        area = int(len(points))
        bbox_area = max(1, bh*bw)
        fill = area / bbox_area
        aspect = max(bh, bw) / max(1.0, min(bh, bw))
        edge_touch = float(np.mean((ys == 0) | (ys == h-1) | (xs == 0) | (xs == w-1)))
        records.append({
            'ys': ys, 'xs': xs, 'area': area, 'height': bh, 'width': bw,
            'fill': float(fill), 'aspect': float(aspect), 'edge_touch': edge_touch,
            'mean_score': float(np.mean(score[ys, xs])),
            'max_score': float(np.max(score[ys, xs])),
        })
    return records



def _detect_diagonal_stripes(
    z: np.ndarray,
    radius_norm: np.ndarray,
    dc_protection: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, list[dict[str, Any]], float | None]:
    """Detect oblique k-space spike trains and coherent diagonal stripes.

    Bright candidates are projected onto angle-dependent normal coordinates.
    A valid artifact must remain inside a narrow normal band and span a large
    distance along the tested direction. Only the strongest non-duplicate
    lines are converted into the final editable mask.
    """
    rows, cols = z.shape
    yy, xx = np.indices(z.shape, dtype=float)
    x = xx - (cols - 1.0) / 2.0
    y = yy - (rows - 1.0) / 2.0
    # Diagonal spike trains are normally strong outliers. Keeping the seed
    # threshold high prevents chance alignments of ordinary k-space texture.
    seed = (z > max(4.0, threshold + 0.35)) & ~dc_protection
    ys, xs = np.where(seed)
    if len(ys) < 5:
        return np.zeros_like(seed), [], None
    px, py, pz = x[ys, xs], y[ys, xs], z[ys, xs]
    diagonal_length = float(np.hypot(rows, cols))
    min_span = max(12.0, 0.20 * diagonal_length)
    min_points = max(5, int(round(min(rows, cols) / 40.0)))
    raw: list[dict[str, Any]] = []

    for angle in range(10, 171, 5):
        if 80 <= angle <= 100:
            continue
        theta = np.deg2rad(float(angle))
        ct, st = float(np.cos(theta)), float(np.sin(theta))
        along = px * ct + py * st
        normal = -px * st + py * ct
        bin_width = 1.5
        bins = np.rint(normal / bin_width).astype(int)
        for key in np.unique(bins):
            idx = np.where(bins == key)[0]
            if idx.size < min_points:
                continue
            coords = along[idx]
            span = float(np.ptp(coords))
            if span < min_span:
                continue
            normal_std = float(np.std(normal[idx]))
            if normal_std > 1.35:
                continue
            ordered = np.sort(coords)
            gaps = np.diff(ordered)
            median_gap = float(np.median(gaps)) if gaps.size else span
            expected_gap = span / max(idx.size - 1, 1)
            continuity = float(np.clip(1.0 - median_gap / max(expected_gap * 3.0, 1.0), 0.0, 1.0))
            occupancy = float(np.clip(idx.size / max(span / 7.0, 1.0), 0.0, 1.0))
            strength = float(np.clip((np.mean(pz[idx]) - 3.5) / 6.0, 0.0, 1.0))
            linearity = float(np.clip(1.0 - normal_std / 1.35, 0.0, 1.0))
            confidence = float(np.clip(0.30*strength + 0.28*occupancy + 0.27*linearity + 0.15*continuity, 0.0, 1.0))
            if confidence < 0.58:
                continue
            raw.append({
                'angle_degrees': float(angle), 'length': span,
                'support': int(idx.size), 'continuity': continuity,
                'linearity': linearity, 'mean_z': float(np.mean(pz[idx])),
                'confidence': confidence, '_idx': idx,
                '_normal_center': float(key)*bin_width,
                '_along_min': float(coords.min()), '_along_max': float(coords.max()),
            })

    if not raw:
        return np.zeros_like(seed), [], None
    raw.sort(key=lambda item: (item['confidence'], item['length'], item['support']), reverse=True)
    accepted: list[dict[str, Any]] = []
    for rec in raw:
        # A Hermitian pair may generate two parallel records. Keep both when
        # spatially distinct, but suppress angle/position duplicates.
        duplicate = any(
            abs(rec['angle_degrees']-old['angle_degrees']) <= 5.0 and
            abs(rec['_normal_center']-old['_normal_center']) <= 3.0
            for old in accepted
        )
        if duplicate:
            continue
        accepted.append(rec)
        if len(accepted) >= 6:
            break

    result = np.zeros_like(seed)
    for rec in accepted:
        theta=np.deg2rad(rec['angle_degrees']); ct=float(np.cos(theta)); st=float(np.sin(theta))
        all_along=x*ct+y*st; all_normal=-x*st+y*ct
        half_width=1.7 if rec['support'] < 10 else 2.3
        geometric=(np.abs(all_normal-rec['_normal_center'])<=half_width)&(all_along>=rec['_along_min']-3.0)&(all_along<=rec['_along_max']+3.0)
        local=geometric&(z>max(1.45,threshold*0.34))&~dc_protection
        idx=rec['_idx']; local[ys[idx],xs[idx]]=True
        result |= dilate(local,1)&~dc_protection
        rec['width']=float(2.0*half_width+1.0)

    public=[]
    for rec in accepted:
        public.append({k:v for k,v in rec.items() if not k.startswith('_')})
    best_angle=float(public[0]['angle_degrees']) if public else None
    return _connected_filter(result,3), public, best_angle

def detect_artifacts(
    kspace: np.ndarray,
    artifact_type: str = "Auto",
    threshold_sigma: float = 4.0,
    sensitivity: str = "Balanced",
) -> ArtifactMaskResult:
    """MRI Auto Detection v4 with robust Spike and Block candidate scoring.

    Spike detection combines robust global excess, multi-scale local contrast,
    isolation, sharpness and symmetry. Block detection evaluates connected
    components by density, compactness, aspect ratio, surrounding contrast and
    edge contact. Normal central k-space energy remains protected.
    """
    source = np.asarray(kspace)
    if source.ndim != 2 or min(source.shape) < 4:
        raise ValueError("Auto Artifact Detection requires a 2D k-space array.")
    mag = np.abs(source)
    logmag = np.log1p(mag)
    med, sigma = robust_stats(logmag)
    z = (logmag - med) / max(sigma, 1e-12)
    threshold = float(np.clip(threshold_sigma, 1.5, 8.0))
    sensitivity_name = str(sensitivity).strip().title()
    if sensitivity_name not in {"Conservative", "Balanced", "Sensitive"}:
        sensitivity_name = "Balanced"

    rows, cols = source.shape
    yy, xx = np.indices(source.shape, dtype=float)
    cy, cx = (rows - 1.0) / 2.0, (cols - 1.0) / 2.0
    radius_norm = np.hypot((yy-cy)/max(rows/2.0,1.0), (xx-cx)/max(cols/2.0,1.0))
    dc_protection = radius_norm < 0.10
    centre_transition = radius_norm < 0.18

    # Existing coherent line/band/ring detectors.
    row_profile = np.percentile(logmag, 70, axis=1)
    col_profile = np.percentile(logmag, 70, axis=0)
    row_med, row_sig = robust_stats(row_profile)
    col_med, col_sig = robust_stats(col_profile)
    row_z = (row_profile-row_med)/max(row_sig,1e-12)
    col_z = (col_profile-col_med)/max(col_sig,1e-12)
    line_pixel_threshold = max(1.85, threshold*0.58)
    row_high = z > line_pixel_threshold
    col_high = row_high
    row_occupancy = np.mean(row_high, axis=1)
    col_occupancy = np.mean(col_high, axis=0)

    # A genuine coherent line must be supported over a meaningful span.  This
    # rejects isolated anatomical/normal k-space columns that previously made
    # the vertical-line detector too eager.
    row_outer = radius_norm >= 0.18
    col_outer = row_outer
    row_outer_occupancy = np.sum(row_high & row_outer, axis=1) / np.maximum(np.sum(row_outer, axis=1), 1)
    col_outer_occupancy = np.sum(col_high & col_outer, axis=0) / np.maximum(np.sum(col_outer, axis=0), 1)
    row_quarters = np.stack([np.mean(row_high[:, a:b], axis=1) for a,b in ((0,max(1,cols//4)),(cols//4,max(cols//4+1,cols//2)),(cols//2,max(cols//2+1,3*cols//4)),(3*cols//4,cols))],axis=1)
    col_quarters = np.stack([np.mean(col_high[a:b, :], axis=0) for a,b in ((0,max(1,rows//4)),(rows//4,max(rows//4+1,rows//2)),(rows//2,max(rows//2+1,3*rows//4)),(3*rows//4,rows))],axis=1)
    row_span_support = np.count_nonzero(row_quarters > 0.025, axis=1) >= 2
    col_span_support = np.count_nonzero(col_quarters > 0.035, axis=1) >= 3

    line_rows = (row_z > 3.05) & (row_occupancy > 0.070) & (row_outer_occupancy > 0.060) & row_span_support
    # Vertical lines were over-selected: require stronger profile excess,
    # greater occupancy, and support in at least three image quarters.
    line_cols = (col_z > 3.55) & (col_occupancy > 0.105) & (col_outer_occupancy > 0.090) & col_span_support
    line_support = line_rows[:,None] | line_cols[None,:]
    line_mask = line_support & (z > np.where(centre_transition, max(3.2,threshold*0.90), max(1.35,threshold*0.42)))
    line_mask &= ~dc_protection
    line_mask = _connected_filter(line_mask, 3)
    band_mask = dilate(line_support,2) & (z > np.where(centre_transition,max(3.0,threshold*0.85),max(0.85,threshold*0.28)))
    band_mask &= ~dc_protection
    band_mask = _connected_filter(band_mask,6)

    rr = np.hypot(yy-cy, xx-cx)
    bins = np.clip(rr.astype(int),0,max(source.shape))
    radial_sum=np.bincount(bins.ravel(),weights=logmag.ravel())
    radial_n=np.bincount(bins.ravel())
    radial=radial_sum/np.maximum(radial_n,1)
    smooth=np.convolve(radial,np.ones(7)/7.0,mode='same')
    residual=radial-smooth
    valid_radial=radial_n > max(6,int(min(rows,cols)*0.08))
    rm,rs=robust_stats(residual[valid_radial])
    ring_bins=valid_radial & (residual > rm+3.25*rs)
    ring_mask=ring_bins[bins] & (z > np.where(centre_transition,max(3.5,threshold),max(1.15,threshold*0.36))) & ~dc_protection
    ring_mask=_connected_filter(ring_mask,max(8,int(min(rows,cols)*0.08)))

    # Spike v2: multi-scale local background contrast and isolation.
    local3 = _box_mean(logmag,1)
    local5 = _box_mean(logmag,2)
    local7 = _box_mean(logmag,3)
    c3 = (logmag-local3)/max(sigma,1e-12)
    c5 = (logmag-local5)/max(sigma,1e-12)
    c7 = (logmag-local7)/max(sigma,1e-12)
    contrast = np.maximum.reduce([c3,c5,c7])
    neighbourhood = np.zeros(source.shape,dtype=np.int16)
    seed_high = z > max(2.5, threshold*0.72)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dy or dx:
                neighbourhood += shift_no_wrap(seed_high,dy,dx,False).astype(np.int16)
    sharpness = logmag - np.maximum.reduce([
        shift_no_wrap(logmag,-1,0,-np.inf), shift_no_wrap(logmag,1,0,-np.inf),
        shift_no_wrap(logmag,0,-1,-np.inf), shift_no_wrap(logmag,0,1,-np.inf)])
    sharpness_z = sharpness/max(sigma,1e-12)
    spike_score = 0.45*np.maximum(z-threshold,0) + 0.35*np.maximum(contrast-2.0,0) + 0.20*np.maximum(sharpness_z-0.5,0)
    spike_seed = (z > threshold) & (contrast > 2.2) & (sharpness_z > 0.35) & (neighbourhood <= 4)
    spike_seed &= ~dilate(line_mask|ring_mask,1) & ~dc_protection
    spike_seed &= (~centre_transition | ((z > threshold+2.4) & (contrast > 3.5)))
    spike_records = _component_records(spike_seed, spike_score)
    spike_mask = np.zeros_like(spike_seed)
    spike_candidates=[]
    for rec in spike_records:
        # True spikes should be tiny/compact, highly isolated and high contrast.
        size_ok = rec['area'] <= max(12, int(0.0008*source.size))
        shape_ok = rec['aspect'] <= 4.0 and rec['fill'] >= 0.20
        score = float(np.clip(0.35*np.tanh(rec['mean_score']/2.0) + 0.30*np.tanh(rec['max_score']/3.0) + 0.20*(1.0-min(rec['area']/12.0,1.0)) + 0.15*(1.0-rec['edge_touch']),0,1))
        if size_ok and shape_ok and score >= 0.42:
            spike_mask[rec['ys'],rec['xs']] = True
            spike_candidates.append({k:v for k,v in rec.items() if k not in ('ys','xs')} | {'confidence':score})

    # Block v3: detect coherent rectangular energy even when every pixel is not
    # individually extreme.  Multi-scale local means join fragmented interiors,
    # while line/ring/spike and the protected DC core remain excluded.
    block_local3 = _box_mean(z, 1)
    block_local5 = _box_mean(z, 2)
    block_local7 = _box_mean(z, 3)
    block_response = np.maximum.reduce([block_local3, block_local5, block_local7])
    block_pixel = z > np.where(centre_transition, max(4.8, threshold+1.7), max(1.75, threshold*0.48))
    block_coherent = block_response > np.where(centre_transition, max(3.8, threshold+0.8), max(1.05, threshold*0.28))
    block_seed = (block_pixel | (block_coherent & (z > max(1.15, threshold*0.30))))
    # Do not subtract line/band candidates here: a real rectangular block can
    # raise several adjacent row/column profiles and was previously erased as
    # a 'line' before geometry scoring. Thin lines are rejected below by area,
    # fill, aspect and surround-contrast checks.
    # Block patterns can also elevate radial bins; do not let the broad Ring
    # proposal erase compact rectangular evidence before geometry scoring.
    block_seed &= ~dilate(spike_mask,1) & ~dc_protection
    # Close one-pixel gaps without scipy, then keep meaningful islands.
    block_seed = dilate(block_seed,1) & (dilate(block_coherent,1) | block_pixel)

    # Commit0096 Block v4: the real-world pattern can consist of several short,
    # aligned rectangular lobes separated by small gaps.  Build a secondary
    # anisotropic grouping mask that bridges short horizontal/vertical gaps but
    # does not turn a single thin line into a block.
    moderate = (z > np.where(centre_transition, max(4.2, threshold + 1.1), max(1.20, threshold * 0.30)))
    moderate &= (block_response > np.where(centre_transition, 2.8, 0.72))
    moderate &= ~dc_protection
    grouped = moderate.copy()
    for dy, dx in ((0,-3),(0,-2),(0,-1),(0,1),(0,2),(0,3),(-1,0),(1,0)):
        grouped |= shift_no_wrap(moderate, dy, dx, False)
    # Require local thickness in at least one direction. This preserves the
    # rectangular bars in the supplied example while rejecting isolated lines.
    thick_h = grouped & shift_no_wrap(grouped,-1,0,False) & shift_no_wrap(grouped,1,0,False)
    thick_v = grouped & shift_no_wrap(grouped,0,-1,False) & shift_no_wrap(grouped,0,1,False)
    grouped = dilate(thick_h | thick_v, 1) & dilate(moderate, 2)
    # Score the original moderate islands as well as grouped candidates. This
    # prevents several aligned bars from becoming one sparse mega-component.
    moderate_records = _component_records(_connected_filter(moderate, 3), np.maximum(z, block_response))
    block_seed |= grouped
    block_seed = _connected_filter(block_seed,3)
    block_records = moderate_records + _component_records(block_seed, np.maximum(z, block_response))
    block_mask=np.zeros_like(block_seed)
    block_candidates=[]
    for rec in block_records:
        comp=np.zeros_like(block_seed); comp[rec['ys'],rec['xs']]=True
        halo=dilate(comp,2)&~comp
        halo_vals=logmag[halo]
        halo_med=float(np.median(halo_vals)) if halo_vals.size else med
        interior=float(np.median(logmag[comp]))
        contrast_score=max(0.0,(interior-halo_med)/max(sigma,1e-12))
        area_ok=3 <= rec['area'] <= max(40,int(0.075*source.size))
        # Fragmented rectangular groups may have a lower fill ratio after small
        # gaps are bridged; retain them when their bounding box has thickness.
        bbox_h = int(rec.get('height', 1)); bbox_w = int(rec.get('width', 1))
        has_thickness = min(bbox_h, bbox_w) >= 3
        compact_ok=(rec['fill'] >= 0.24 and rec['aspect'] <= 8.0 and has_thickness)
        edge_penalty=1.0-min(1.0,rec['edge_touch']*1.5)
        scale_support=float(np.mean(block_response[comp])) if np.any(comp) else 0.0
        score=float(np.clip(0.29*np.tanh(contrast_score/2.0)+0.20*rec['fill']+0.15*(1.0-min(abs(np.log(max(rec['aspect'],1e-6)))/2.3,1.0))+0.18*np.tanh(rec['mean_score']/3.2)+0.10*np.tanh(scale_support/2.0)+0.08*edge_penalty,0,1))
        mirrored_support = float(np.mean(block_response[np.flip(np.flip(comp,0),1)])) if np.any(comp) else 0.0
        pair_bonus = 0.05 if mirrored_support >= 0.70 else 0.0
        score = float(np.clip(score + pair_bonus, 0, 1))
        if area_ok and compact_ok and contrast_score >= 0.78 and scale_support >= 0.68 and score >= 0.34:
            block_mask[rec['ys'],rec['xs']]=True
            block_candidates.append({k:v for k,v in rec.items() if k not in ('ys','xs')} | {'surround_contrast':contrast_score,'confidence':score})

    # Diagonal detector: handles both continuous oblique bands and sparse
    # spike trains that reconstruct as diagonal image stripes.
    # Commit0097: normal-signal preservation guard. Smooth radial k-space
    # energy and the central phase-encoding/readout cross are common image-
    # forming signals, not artifacts. They are protected unless a candidate
    # has strong local contrast or candidate-specific geometric evidence.
    radial_expected = radial[np.clip(bins, 0, len(radial)-1)]
    radial_residual_z = (logmag - radial_expected) / max(sigma, 1e-12)
    local_structure_contrast = np.maximum.reduce([np.abs(c3), np.abs(c5), np.abs(c7)])
    axis_distance = np.minimum(np.abs(yy-cy)/max(rows,1), np.abs(xx-cx)/max(cols,1))
    smooth_radial_signal = (radius_norm < 0.42) & (radial_residual_z < 2.15) & (local_structure_contrast < 1.65)
    central_axis_signal = (radius_norm < 0.52) & (axis_distance < 0.012) & (local_structure_contrast < 2.20)
    normal_signal_guard = (smooth_radial_signal | central_axis_signal) & ~dc_protection
    # Line/Band/Ring are the most likely to absorb valid image-forming signal.
    # Spike/Block/Diagonal already require local or geometric evidence and are
    # therefore only guarded in the very smooth central transition region.
    line_mask &= ~normal_signal_guard
    band_mask &= ~normal_signal_guard
    ring_mask &= ~normal_signal_guard
    weak_block_guard = normal_signal_guard & (block_response < 1.45) & (z < max(3.5, threshold*0.90))
    block_mask &= ~weak_block_guard

    diagonal_mask, diagonal_candidates, diagonal_angle = _detect_diagonal_stripes(
        z, radius_norm, dc_protection, threshold
    )
    # Keep spike candidates independent from diagonal candidates. A single
    # true spike can participate in several projection hypotheses; typed Spike
    # mode must not lose it merely because the diagonal detector also fired.

    row_strength=float(np.max(row_z)) if row_z.size else 0.0
    col_strength=float(np.max(col_z)) if col_z.size else 0.0
    direction='Horizontal' if row_strength > col_strength*1.10 else 'Vertical'
    if max(row_strength,col_strength)<=0 or abs(row_strength-col_strength)<=0.10*max(row_strength,col_strength,1e-12):
        direction='Isotropic'
    diagonal_coherence=max([c['confidence'] for c in diagonal_candidates],default=0.0)
    if diagonal_angle is not None and diagonal_coherence >= 0.48:
        direction=f'Diagonal {diagonal_angle:.1f}°'

    candidates={'spike':spike_mask,'line':line_mask,'band':band_mask,'block':block_mask,'ring':ring_mask,'diagonal':diagonal_mask}
    coherences={'spike':max([c['confidence'] for c in spike_candidates],default=0.0),'line':min(1.0,max(row_strength,col_strength)/6.0),'band':min(1.0,max(row_strength,col_strength)/5.0),'block':max([c['confidence'] for c in block_candidates],default=0.0),'ring':min(1.0,float(np.count_nonzero(ring_bins))/3.0),'diagonal':diagonal_coherence}
    confidences={name:_candidate_confidence(mask,np.maximum(z-1.0,0.0),coherences[name]) for name,mask in candidates.items()}
    # Candidate-level evidence is more reliable for Spike/Block than coverage.
    confidences['spike']=max(confidences['spike'],coherences['spike']) if np.any(spike_mask) else 0.0
    confidences['block']=max(confidences['block'],coherences['block']) if np.any(block_mask) else 0.0
    confidences['diagonal']=max(confidences['diagonal'],coherences['diagonal']) if np.any(diagonal_mask) else 0.0
    counts={name:int(np.count_nonzero(mask)) for name,mask in candidates.items()}

    normalized=str(artifact_type).strip().lower()
    if normalized=='auto':
        minimum_confidence = {
            "Conservative": 0.60,
            "Balanced": 0.51,
            "Sensitive": 0.43,
        }[sensitivity_name]
        type_offsets = {
            "line": 0.08, "band": 0.08, "ring": 0.06,
            "spike": 0.00, "block": -0.02, "diagonal": 0.00,
        }
        selected_names=[
            n for n,c in confidences.items()
            if c >= minimum_confidence + type_offsets.get(n, 0.0) and counts[n] > 0
        ]

        # Commit0100 Stage-2 artifact validation. Detection confidence alone is
        # insufficient because strong anatomical k-space can resemble lines or
        # blocks. Validate each candidate using independent evidence: local/radial
        # residual, compactness and normal-signal overlap. Only candidates whose
        # expected correction benefit exceeds their structure-loss risk survive.
        validation = {}
        validated_names = []
        for name in selected_names:
            cmask = candidates[name]
            pixels = int(np.count_nonzero(cmask))
            if pixels <= 0:
                continue
            local_evidence = float(np.mean(np.clip(local_structure_contrast[cmask] / 4.0, 0.0, 1.0)))
            radial_evidence = float(np.mean(np.clip(radial_residual_z[cmask] / 5.0, 0.0, 1.0)))
            outlier_evidence = float(np.mean(np.clip((z[cmask] - 2.0) / 5.0, 0.0, 1.0)))
            normal_overlap = float(np.mean(normal_signal_guard[cmask]))
            coverage = float(pixels) / float(max(cmask.size, 1))
            compactness = float(np.clip(1.0 - coverage / 0.08, 0.0, 1.0))
            geometry_bonus = {"spike":0.18,"block":0.16,"diagonal":0.14,"line":0.02,"band":0.02,"ring":0.00}.get(name,0.0)
            benefit = float(np.clip(0.34*local_evidence + 0.26*radial_evidence + 0.22*outlier_evidence + 0.10*compactness + geometry_bonus, 0.0, 1.0))
            structure_risk = float(np.clip(0.72*normal_overlap + 0.28*(1.0-local_evidence), 0.0, 1.0))
            net = benefit - structure_risk
            threshold_net = {"Conservative":0.10,"Balanced":0.02,"Sensitive":-0.06}[sensitivity_name]
            coverage_ceiling = {"spike":0.035,"block":0.055,"diagonal":0.075,"line":0.030,"band":0.050,"ring":0.040}.get(name,0.05)
            accepted = bool(net >= threshold_net and coverage <= coverage_ceiling)
            validation[name] = {
                "benefit": benefit, "structure_risk": structure_risk,
                "net_benefit": float(net), "normal_overlap": normal_overlap,
                "coverage": coverage, "accepted": accepted,
            }
            if accepted:
                validated_names.append(name)
        selected_names = validated_names
        if not selected_names and any(counts.values()):
            best=max(confidences,key=confidences.get)
            fallback = minimum_confidence - (0.08 if sensitivity_name != "Conservative" else 0.04)
            selected_names=[best] if confidences[best]>=fallback else []
        mask=np.logical_or.reduce([candidates[n] for n in selected_names]) if selected_names else np.zeros_like(dc_protection)
        # Final protection pass after combining candidate types. Candidate
        # pixels with strong local evidence remain, while smooth normal signal
        # accidentally absorbed by line/band proposals is removed.
        # Commit0099 precision guard: automatic masks now require agreement
        # between candidate geometry and independent residual evidence.  This
        # prevents smooth image-forming k-space energy from entering the mask
        # merely because it lies on a strong row/column or radial profile.
        candidate_core = spike_mask | block_mask | diagonal_mask
        residual_core = (local_structure_contrast >= 2.45) | (radial_residual_z >= 3.00)
        line_ring_core = (line_mask | band_mask | ring_mask) & residual_core
        mask &= (candidate_core | line_ring_core)
        strong_evidence = candidate_core | (local_structure_contrast >= 2.60) | (radial_residual_z >= 3.20)
        preserve_guard = normal_signal_guard & ~strong_evidence
        mask &= ~preserve_guard

        # Over-selection limiter.  Auto mode should propose a compact artifact
        # mask, not repaint a large fraction of k-space.  When coverage is too
        # high, retain only pixels with the strongest independent evidence and
        # always keep accepted compact Spike/Block/Diagonal cores.
        coverage_limit = {"Conservative": 0.035, "Balanced": 0.060, "Sensitive": 0.095}[sensitivity_name]
        coverage = float(np.count_nonzero(mask)) / float(max(mask.size, 1))
        if coverage > coverage_limit:
            score_map = np.maximum(local_structure_contrast, np.maximum(radial_residual_z, z * 0.55))
            non_core = mask & ~candidate_core
            allowed_non_core = max(0, int(coverage_limit * mask.size) - int(np.count_nonzero(candidate_core)))
            if allowed_non_core <= 0:
                mask = candidate_core.copy()
            elif np.count_nonzero(non_core) > allowed_non_core:
                vals = score_map[non_core]
                kth = max(0, vals.size - allowed_non_core)
                cutoff = float(np.partition(vals, kth)[kth])
                mask = candidate_core | (non_core & (score_map >= cutoff))

        ranked=sorted(confidences,key=confidences.get,reverse=True)
        primary=ranked[0] if ranked and counts[ranked[0]] else 'none'
        artifact_type=primary.title() if selected_names else 'None'
        confidence=max((confidences[n] for n in selected_names),default=0.0)
    else:
        selected=normalized if normalized in candidates else 'spike'
        mask=candidates[selected]; primary=selected
        selected_names=[selected] if counts[selected] else []
        artifact_type=selected.title(); confidence=confidences[selected]

    mask=_mirror_mask_hermitian(mask & ~dc_protection)
    mask=dilate(mask,1)&~dc_protection if np.any(mask) else mask
    # Final compactness governor after Hermitian mirroring and edge dilation.
    # This is deliberately last because those operations can otherwise turn a
    # reasonable proposal into a very large mask. Keep the strongest residual
    # pixels while preserving symmetry.
    if normalized == 'auto' and np.any(mask):
        final_limit = {"Conservative":0.035,"Balanced":0.060,"Sensitive":0.090}[sensitivity_name]
        max_pixels = int(final_limit * mask.size)
        current_pixels = int(np.count_nonzero(mask))
        if current_pixels > max_pixels > 0:
            final_score = np.maximum.reduce([local_structure_contrast, radial_residual_z, np.maximum(z-2.0,0.0)])
            vals = final_score[mask]
            kth = max(0, vals.size - max_pixels)
            cutoff = float(np.partition(vals, kth)[kth])
            mask &= final_score >= cutoff
            mask = _mirror_mask_hermitian(mask & ~dc_protection)
            if np.count_nonzero(mask) > max_pixels:
                # Pair-aware truncation can slightly exceed the target; apply a
                # second exact cutoff without further dilation.
                vals = final_score[mask]
                kth = max(0, vals.size - max_pixels)
                cutoff = float(np.partition(vals, kth)[kth])
                mask &= final_score >= cutoff
    stats={
        'counts':counts,
        'confidences':{k:float(v) for k,v in confidences.items()},
        'selected_types':selected_names,'primary_type':primary.title(),
        'threshold_sigma':threshold,'row_lines':int(np.count_nonzero(line_rows)),
        'col_lines':int(np.count_nonzero(line_cols)),
        'dc_protected_pixels':int(np.count_nonzero(dc_protection)),
        'centre_transition_pixels':int(np.count_nonzero(centre_transition)),
        'centre_guard_radius':0.10,'mask_pixels':int(np.count_nonzero(mask)),
        'normal_signal_guard_pixels':int(np.count_nonzero(normal_signal_guard)),
        'normal_signal_rejected_pixels':int(np.count_nonzero(normal_signal_guard & ~mask)),
        'auto_sensitivity':sensitivity_name,
        'spike_candidates':spike_candidates[:32],
        'block_candidates':block_candidates[:32],
        'diagonal_candidates':diagonal_candidates[:12],
        'diagonal_angle_degrees':diagonal_angle,
        'adaptive_thresholds':{'global_z':threshold,'spike_local_contrast':2.2,'block_surround_contrast':1.05,'vertical_line_profile_z':3.55,'vertical_line_occupancy':0.105,'diagonal_min_confidence':0.48},
        'detector_version':'mri_auto_detection_v5',
        'detector_revision':'mri_auto_detection_v8_stage2_artifact_validation',
        'artifact_validation':validation if normalized=='auto' else {},
        'diagonal_engine_version':'diagonal_artifact_engine_v1',
        'auto_mask_coverage':float(np.count_nonzero(mask))/float(max(mask.size,1)),
    }
    return ArtifactMaskResult(mask,artifact_type,float(np.clip(confidence,0,1)),direction,stats)

def _frequency_weight(shape: tuple[int, int], direction: str) -> np.ndarray:
    y = np.linspace(-1.0, 1.0, shape[0])[:, None]
    x = np.linspace(-1.0, 1.0, shape[1])[None, :]
    radius = np.sqrt(x*x + y*y)
    weight = 0.35 + 0.65 * np.clip(radius, 0.0, 1.0)
    if direction == "Horizontal":
        weight *= 0.75 + 0.25 * np.abs(y)
    elif direction == "Vertical":
        weight *= 0.75 + 0.25 * np.abs(x)
    elif str(direction).startswith("Diagonal"):
        try:
            angle = np.deg2rad(float(str(direction).split()[1].rstrip('°')))
            normal = np.abs(-x * np.sin(angle) + y * np.cos(angle))
            weight *= 0.72 + 0.28 * np.clip(normal, 0.0, 1.0)
        except Exception:
            pass
    return np.clip(weight, 0.25, 1.0)



def _frequency_aware_weight(
    source: np.ndarray,
    mask: np.ndarray,
    direction: str,
    level: str,
) -> tuple[np.ndarray, dict[str, float]]:
    """Build an adaptive low/mid/high-frequency compensation map.

    The DC core is protected, the artifact-bearing radial bands are weighted
    from measured mask energy, and directional emphasis follows the detected
    stripe orientation.  This is intentionally data-driven rather than a fixed
    radial ramp.
    """
    shape = source.shape
    rows, cols = shape
    yy, xx = np.indices(shape, dtype=float)
    cy, cx = (rows - 1.0) / 2.0, (cols - 1.0) / 2.0
    ry = (yy - cy) / max(rows / 2.0, 1.0)
    rx = (xx - cx) / max(cols / 2.0, 1.0)
    radius = np.clip(np.hypot(ry, rx), 0.0, 1.5)

    # Three overlapping bands avoid hard seams in k-space.
    low = np.exp(-0.5 * (radius / 0.22) ** 2)
    mid = np.exp(-0.5 * ((radius - 0.48) / 0.22) ** 2)
    high = 1.0 / (1.0 + np.exp(-(radius - 0.68) * 14.0))

    mag = np.log1p(np.abs(source))
    m = np.asarray(mask, dtype=bool)
    global_med, global_sig = robust_stats(mag[~m] if np.any(~m) else mag)
    band_masks = {
        "low": radius < 0.30,
        "mid": (radius >= 0.25) & (radius < 0.70),
        "high": radius >= 0.62,
    }
    gains: dict[str, float] = {}
    for name, bm in band_masks.items():
        selected = m & bm
        if np.any(selected):
            excess = float(np.median(mag[selected]) - global_med) / max(global_sig, 1e-12)
            gains[name] = float(np.clip(0.55 + 0.10 * max(0.0, excess), 0.45, 1.25))
        else:
            gains[name] = 0.55

    # DC carries most anatomical contrast. Protect it more strongly while still
    # allowing explicit artifacts painted through the centre to be corrected.
    dc_floor = {"Low": 0.18, "Mid": 0.24, "High": 0.30, "Extreme": 0.38}.get(str(level).title(), 0.30)
    radial = gains["low"] * low + gains["mid"] * mid + gains["high"] * high
    radial /= np.maximum(low + mid + high, 1e-12)
    dc_protection = dc_floor + (1.0 - dc_floor) * np.clip(radius / 0.22, 0.0, 1.0)
    weight = radial * dc_protection

    if direction == "Horizontal":
        # Horizontal image stripes map predominantly to a vertical k-space axis.
        directional = 0.62 + 0.38 * np.abs(ry) / np.maximum(radius, 1e-6)
        weight *= directional
    elif direction == "Vertical":
        directional = 0.62 + 0.38 * np.abs(rx) / np.maximum(radius, 1e-6)
        weight *= directional
    elif str(direction).startswith("Diagonal"):
        try:
            angle = np.deg2rad(float(str(direction).split()[1].rstrip('°')))
            normal = np.abs(-rx * np.sin(angle) + ry * np.cos(angle))
            directional = 0.62 + 0.38 * normal / np.maximum(radius, 1e-6)
            weight *= directional
        except Exception:
            pass

    weight = np.clip(weight, 0.12, 1.0)
    metadata = {
        "low_band_gain": gains["low"],
        "mid_band_gain": gains["mid"],
        "high_band_gain": gains["high"],
        "dc_weight": float(weight[int(round(cy)), int(round(cx))]),
        "mean_mask_weight": float(np.mean(weight[m])) if np.any(m) else 0.0,
    }
    return weight, metadata

def roi_statistics(before: np.ndarray, after: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    m = np.asarray(mask, dtype=bool)
    if not np.any(m):
        return {"before_mean": 0.0, "after_mean": 0.0, "before_max": 0.0, "after_max": 0.0, "reduction_percent": 0.0}
    b, a = np.abs(before)[m], np.abs(after)[m]
    bmean, amean = float(np.mean(b)), float(np.mean(a))
    return {
        "before_mean": bmean, "after_mean": amean,
        "before_max": float(np.max(b)), "after_max": float(np.max(a)),
        "reduction_percent": float(100.0 * max(0.0, bmean - amean) / max(bmean, 1e-12)),
    }


def artifact_reduction_score(before: np.ndarray, after: np.ndarray, mask: np.ndarray) -> float:
    stats = roi_statistics(before, after, mask)
    energy_score = np.clip(stats["reduction_percent"] / 100.0, 0.0, 1.0)
    before_img, after_img = np.abs(ifft2c(before)), np.abs(ifft2c(after))
    delta = np.mean(np.abs(after_img - before_img)) / max(np.mean(np.abs(before_img)), 1e-12)
    preservation = np.clip(1.0 - delta, 0.0, 1.0)
    return float(100.0 * (0.75 * energy_score + 0.25 * preservation))


def compensate(
    kspace: np.ndarray,
    mask: np.ndarray | None = None,
    *,
    artifact_type: str = "Auto",
    level: str = "High",
    threshold_sigma: float = 4.0,
    target_ratio: float = 1.0,
    adaptive_direction: bool = True,
    frequency_aware: bool = True,
    harmonic_poisson: bool = True,
    multi_pass: bool = True,
    hermitian_symmetry: bool = True,
    mask_expansion: int | None = None,
    donor_halo: int | None = None,
    pass_count: int | None = None,
    strength_override: float | None = None,
    structure_preservation: float = 0.65,
    detection_sensitivity: str = "Balanced",
) -> CompensationResult:
    source = np.asarray(kspace)
    if source.ndim != 2 or not np.all(np.isfinite(source)):
        raise ValueError("Hybrid Compensation requires a finite 2-D k-space array.")
    # An explicitly supplied mask is authoritative.  Manual Paint, Expert, and
    # Quick Adjust recalculation must not replace it by running candidate
    # detection again.  Detection is used only when no mask was supplied.
    if mask is None:
        detection = detect_artifacts(source, artifact_type, threshold_sigma, detection_sensitivity)
        active_mask = detection.mask
    else:
        active_mask = np.asarray(mask, dtype=bool)
        detection = ArtifactMaskResult(
            mask=active_mask, artifact_type=str(artifact_type), confidence=1.0,
            direction="Isotropic", stats={"source": "explicit_mask"},
        )
    if active_mask.shape != source.shape or not np.any(active_mask):
        raise ValueError("Compensation mask is empty or has an invalid shape.")

    profiles = {
        "Low": (0.45, 1, 1), "Mid": (0.75, 2, 2),
        "High": (0.98, 3, 4), "Extreme": (1.00, 5, 6),
    }
    strength, passes, expansion = profiles.get(str(level).title(), profiles["High"])
    if strength_override is not None:
        strength = float(np.clip(strength_override, 0.05, 1.0))
    if mask_expansion is not None:
        expansion = int(np.clip(mask_expansion, 0, 10))
    if pass_count is not None:
        passes = int(np.clip(pass_count, 1, 6))
    donor_radius = 2 + expansion if donor_halo is None else int(np.clip(donor_halo, 1, 14))
    work_mask = dilate(active_mask, expansion)
    donor_mask = dilate(work_mask, donor_radius)
    result = source.copy()
    direction = detection.direction if adaptive_direction else "Isotropic"
    if frequency_aware:
        fweight, frequency_report = _frequency_aware_weight(source, work_mask, direction, level)
    else:
        fweight, frequency_report = np.ones(source.shape), {
            "low_band_gain": 1.0, "mid_band_gain": 1.0, "high_band_gain": 1.0,
            "dc_weight": 1.0, "mean_mask_weight": 1.0,
        }
    actual_passes = passes if multi_pass else 1

    # Normal-signal preservation is a soft limiter, not a hard exclusion. It
    # reduces blending where k-space follows a smooth radial/local background,
    # while leaving isolated or geometrically coherent artifacts fully exposed.
    preservation = float(np.clip(structure_preservation, 0.0, 1.0))
    logmag = np.log1p(np.abs(source))
    med_log, sig_log = robust_stats(logmag)
    yy, xx = np.indices(source.shape, dtype=float)
    cy, cx = (source.shape[0]-1.0)/2.0, (source.shape[1]-1.0)/2.0
    rr = np.hypot(yy-cy, xx-cx).astype(int)
    radial_sum = np.bincount(rr.ravel(), weights=logmag.ravel())
    radial_count = np.bincount(rr.ravel())
    radial_mean = radial_sum / np.maximum(radial_count, 1)
    radial_model = radial_mean[np.clip(rr, 0, len(radial_mean)-1)]
    local_model = _box_mean(logmag, 2)
    radial_deviation = np.abs(logmag-radial_model)/max(sig_log,1e-12)
    local_deviation = np.abs(logmag-local_model)/max(sig_log,1e-12)
    normal_likelihood = np.exp(-0.85*radial_deviation) * np.exp(-0.65*local_deviation)
    radius_norm = np.hypot((yy-cy)/max(source.shape[0]/2.0,1.0),(xx-cx)/max(source.shape[1]/2.0,1.0))
    normal_likelihood *= np.clip(1.20-radius_norm,0.0,1.0)

    poisson_reports: list[dict[str, float]] = []
    for pass_index in range(actual_passes):
        valid = ~donor_mask
        fallback = np.median(result[valid]) if np.any(valid) else 0.0
        row_model = np.empty_like(result)
        col_model = np.empty_like(result)
        for row in range(source.shape[0]):
            vals = result[row, valid[row]]
            row_model[row, :] = np.median(vals) if vals.size else fallback
        for col in range(source.shape[1]):
            vals = result[valid[:, col], col]
            col_model[:, col] = np.median(vals) if vals.size else fallback
        structured = 0.5 * (row_model + col_model)
        if direction == "Horizontal": structured = 0.7 * row_model + 0.3 * col_model
        if direction == "Vertical": structured = 0.3 * row_model + 0.7 * col_model

        if harmonic_poisson:
            # A genuine guided Poisson solve: the structured background supplies
            # the right-hand side while unmasked k-space supplies Dirichlet edges.
            model, report = _poisson_fill(
                result,
                donor_mask,
                guidance=structured,
                iterations=320 + 160 * pass_index,
                omega=1.72 if str(level).title() in {"High", "Extreme"} else 1.55,
                tolerance=1e-7,
            )
        else:
            model, report = _poisson_fill(result, donor_mask, iterations=1, omega=1.0)
        poisson_reports.append(report)
        model = 0.82 * model + 0.18 * structured
        model *= float(np.clip(target_ratio, 0.25, 2.0))
        preservation_limiter = np.clip(1.0 - preservation * normal_likelihood, 0.08, 1.0)
        pass_strength = np.clip(strength * fweight * preservation_limiter * (0.82 + 0.18 * (pass_index + 1) / actual_passes), 0.0, 1.0)
        result[work_mask] = result[work_mask] * (1.0 - pass_strength[work_mask]) + model[work_mask] * pass_strength[work_mask]

    if hermitian_symmetry:
        result = enforce_hermitian(result, work_mask)
    before_image, after_image = ifft2c(source), ifft2c(result)
    diff_fft = np.abs(result - source)
    diff_phase = np.angle(result * np.conj(source) + 1e-12)
    diff_image = np.abs(after_image) - np.abs(before_image)
    metrics = roi_statistics(source, result, work_mask)
    metrics["artifact_reduction_score"] = artifact_reduction_score(source, result, work_mask)
    metrics["changed_pixels"] = float(np.count_nonzero(work_mask))
    return CompensationResult(
        result, np.abs(after_image), diff_fft, diff_phase, diff_image, work_mask,
        metrics,
        {
            "artifact_type": detection.artifact_type, "direction": direction,
            "confidence": detection.confidence, "level": str(level).title(),
            "passes": actual_passes, "frequency_aware": bool(frequency_aware),
            "frequency_model": "adaptive_three_band_directional_v2" if frequency_aware else "disabled",
            "frequency_band_gains": frequency_report,
            "harmonic_poisson": bool(harmonic_poisson),
            "poisson_solver": "guided_red_black_sor" if harmonic_poisson else "disabled",
            "poisson_iterations": [int(r["iterations"]) for r in poisson_reports],
            "poisson_residuals": [float(r["residual"]) for r in poisson_reports],
            "poisson_converged": [bool(r["converged"]) for r in poisson_reports],
            "hermitian_symmetry": bool(hermitian_symmetry),
            "mask_expansion": int(expansion),
            "donor_halo": int(donor_radius),
            "strength": float(strength),
            "structure_preservation": float(preservation),
            "detection_sensitivity": str(detection_sensitivity),
        },
    )
