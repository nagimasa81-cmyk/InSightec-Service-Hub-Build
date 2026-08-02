from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


class RawImportError(RuntimeError):
    pass


@dataclass
class RawImportResult:
    path: Path
    data: np.ndarray
    rows: int
    cols: int
    dtype_name: str
    endian_name: str
    offset_bytes: int
    is_kspace: bool
    confidence: float
    reason: str
    recommended_display: str = "Auto"
    fus_image_likeness: float = 0.0
    experimental: bool = False
    candidate_summary: str = ""


@dataclass
class _Candidate:
    rows: int
    cols: int
    dtype: np.dtype
    dtype_name: str
    endian_name: str
    offset: int
    is_complex: bool
    score: float = -1e9
    reason: str = ""
    fus_image_likeness: float = -1.0


_COMMON_DIMS = (
    64, 96, 128, 160, 192, 224, 240, 256, 288, 320, 384,
    448, 480, 512, 576, 640, 768, 896, 1024, 1280, 1536, 2048,
)
_OFFSETS = (0, 128, 256, 512, 1024, 2048, 4096, 6144, 8192, 16384)


def try_render_fus_raw_exact(path: Path) -> Optional[RawImportResult]:
    """Exact RAW preview decoder from FUS Investigation Replay Commit0013.

    Candidate order, data types, matrix widths, 1–99% normalization,
    adjacent-pixel correlation and rectangular penalty intentionally match
    the referenced tool.
    """
    path = Path(path)
    try:
        blob = path.read_bytes()
    except Exception:
        return None

    candidates = []
    for dtype_name in ("<u2", "<i2", "<f4"):
        try:
            array = np.frombuffer(blob, dtype=dtype_name)
        except Exception:
            continue

        if array.size < 4096:
            continue

        for width in (128, 192, 256, 320, 384, 448, 512, 640, 768, 1024):
            if array.size % width:
                continue

            height = array.size // width
            if not (64 <= height <= 2048):
                continue

            candidate = array.reshape(height, width).astype(float)
            finite = np.isfinite(candidate)
            if finite.mean() < 0.98:
                continue

            p1, p99 = np.percentile(candidate[finite], [1, 99])
            if p99 <= p1:
                continue

            normalized = np.clip((candidate - p1) / (p99 - p1), 0, 1)

            corr_x = (
                np.corrcoef(
                    normalized[:, :-1].ravel(),
                    normalized[:, 1:].ravel(),
                )[0, 1]
                if width > 2
                else 0
            )
            corr_y = (
                np.corrcoef(
                    normalized[:-1, :].ravel(),
                    normalized[1:, :].ravel(),
                )[0, 1]
                if height > 2
                else 0
            )
            score = np.nan_to_num((corr_x + corr_y) / 2)
            score -= 0.0001 * abs(width - height)
            candidates.append(
                (
                    float(score),
                    dtype_name,
                    width,
                    height,
                    normalized,
                    float(np.nan_to_num(corr_x)),
                    float(np.nan_to_num(corr_y)),
                )
            )

    if not candidates:
        return None

    score, dtype_name, width, height, normalized, corr_x, corr_y = max(
        candidates,
        key=lambda item: item[0],
    )

    dtype_labels = {
        "<u2": "Unsigned Int16",
        "<i2": "Signed Int16",
        "<f4": "Float32",
    }

    return RawImportResult(
        path=path,
        data=np.asarray(normalized, dtype=np.float32),
        rows=int(height),
        cols=int(width),
        dtype_name=dtype_labels.get(dtype_name, dtype_name),
        endian_name="Little Endian",
        offset_bytes=0,
        is_kspace=False,
        confidence=float(np.clip((score + 1.0) / 2.0, 0.0, 1.0)),
        reason=(
            "Exact FUS Commit0013 decoder; "
            f"adjacent correlation X={corr_x:.3f}, Y={corr_y:.3f}, "
            f"image-likeness={score:.3f}"
        ),
        recommended_display="Direct Array",
        fus_image_likeness=float(score),
    )


def _safe_cache_read(path: Optional[Path]) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _safe_cache_write(path: Optional[Path], value: dict) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _profile_key(path: Path) -> str:
    return f"{path.suffix.lower()}:{path.stat().st_size}"


def _dtype_candidates() -> list[tuple[np.dtype, str, str, bool]]:
    values = []
    for endian, endian_name in (("<", "Little Endian"), (">", "Big Endian")):
        values.extend([
            (np.dtype(endian + "i2"), "Signed Int16", endian_name, False),
            (np.dtype(endian + "u2"), "Unsigned Int16", endian_name, False),
            (np.dtype(endian + "f4"), "Float32", endian_name, False),
            (np.dtype(endian + "c8"), "Complex Float32", endian_name, True),
        ])
    # Interleaved complex int16 is handled separately.
    values.extend([
        (np.dtype("<i2"), "Complex Int16", "Little Endian", True),
        (np.dtype(">i2"), "Complex Int16", "Big Endian", True),
    ])
    return values


def _matrix_shapes(element_count: int) -> list[tuple[int, int]]:
    shapes = set()
    side = int(round(math.sqrt(element_count)))
    if side * side == element_count:
        shapes.add((side, side))

    for rows in _COMMON_DIMS:
        if element_count % rows == 0:
            cols = element_count // rows
            if 32 <= cols <= 4096:
                ratio = max(rows, cols) / max(min(rows, cols), 1)
                if ratio <= 8.0:
                    shapes.add((rows, cols))
    return sorted(
        shapes,
        key=lambda rc: (
            abs(math.log(max(rc) / max(min(rc), 1))),
            abs(rc[0] - rc[1]),
        ),
    )[:40]


def _decode_candidate(path: Path, candidate: _Candidate) -> np.ndarray:
    raw = np.fromfile(path, dtype=candidate.dtype, offset=candidate.offset)
    expected = candidate.rows * candidate.cols

    if candidate.dtype_name == "Complex Int16":
        needed = expected * 2
        if raw.size < needed:
            raise RawImportError("Complex Int16 candidate is shorter than expected.")
        paired = raw[:needed].reshape((-1, 2))
        data = paired[:, 0].astype(np.float32) + 1j * paired[:, 1].astype(np.float32)
    else:
        if raw.size < expected:
            raise RawImportError("RAW candidate is shorter than expected.")
        data = raw[:expected]

    return data.reshape((candidate.rows, candidate.cols))


def _safe_corrcoef(a: np.ndarray, b: np.ndarray) -> float:
    left = np.asarray(a, dtype=float).ravel()
    right = np.asarray(b, dtype=float).ravel()
    valid = np.isfinite(left) & np.isfinite(right)
    if int(np.sum(valid)) < 64:
        return 0.0
    left = left[valid]
    right = right[valid]
    if float(np.std(left)) < 1e-12 or float(np.std(right)) < 1e-12:
        return 0.0
    value = float(np.corrcoef(left, right)[0, 1])
    return value if np.isfinite(value) else 0.0


def _fus_image_likeness(array: np.ndarray) -> tuple[float, str]:
    """FUS Investigation Replay compatible RAW image-likeness score."""
    source = np.asarray(array)
    if np.iscomplexobj(source):
        source = np.abs(source)
    source = np.asarray(source, dtype=float)
    finite = np.isfinite(source)
    if float(np.mean(finite)) < 0.98:
        return -1.0, "insufficient finite values"

    values = source[finite]
    if values.size < 4096:
        return -1.0, "too few samples"

    p1, p99 = np.percentile(values, [1.0, 99.0])
    if not np.isfinite(p1) or not np.isfinite(p99) or p99 <= p1:
        return -1.0, "invalid 1–99% dynamic range"

    normalized = np.clip((source - p1) / (p99 - p1), 0.0, 1.0)
    corr_x = (
        _safe_corrcoef(normalized[:, :-1], normalized[:, 1:])
        if normalized.shape[1] > 2 else 0.0
    )
    corr_y = (
        _safe_corrcoef(normalized[:-1, :], normalized[1:, :])
        if normalized.shape[0] > 2 else 0.0
    )
    likeness = float((corr_x + corr_y) / 2.0)
    likeness -= 0.0001 * abs(normalized.shape[1] - normalized.shape[0])
    return likeness, (
        f"FUS adjacent correlation X={corr_x:.3f}, "
        f"Y={corr_y:.3f}, likeness={likeness:.3f}"
    )


def _entropy_score(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size < 32:
        return -5.0
    low, high = np.percentile(finite, [1.0, 99.0])
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        return -5.0
    hist, _ = np.histogram(finite, bins=64, range=(low, high))
    probabilities = hist.astype(float)
    probabilities /= max(probabilities.sum(), 1.0)
    probabilities = probabilities[probabilities > 0]
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return float(entropy / 6.0)


def _score_candidate(array: np.ndarray, is_complex: bool) -> tuple[float, str, float]:
    data = np.asarray(array)
    magnitude = np.abs(data) if np.iscomplexobj(data) else np.asarray(data, dtype=float)
    finite = magnitude[np.isfinite(magnitude)]
    if finite.size < 128:
        return -100.0, "Too few finite samples", -1.0

    zero_fraction = float(np.mean(finite == 0))
    unique_estimate = np.unique(finite[: min(finite.size, 20000)]).size
    low, median, high = np.percentile(finite, [1.0, 50.0, 99.5])
    spread = float(high - low)
    robust_scale = float(np.median(np.abs(finite - median)) * 1.4826)
    dynamic = spread / max(robust_scale, 1e-9)

    score = 0.0
    reasons = []

    if zero_fraction < 0.98:
        score += 1.0
        reasons.append("non-empty")
    else:
        score -= 5.0

    if unique_estimate >= 32:
        score += 1.0
        reasons.append("sufficient variation")
    else:
        score -= 4.0

    if np.isfinite(dynamic) and 1.5 <= dynamic <= 1e6:
        score += min(math.log10(max(dynamic, 1.0)), 4.0) * 0.45
        reasons.append("plausible dynamic range")
    else:
        score -= 2.0

    score += _entropy_score(finite)

    # MRI-like frequency structure: energy is neither completely uniform nor a single constant.
    sample = magnitude
    if max(sample.shape) > 512:
        step_y = max(1, sample.shape[0] // 512)
        step_x = max(1, sample.shape[1] // 512)
        sample = sample[::step_y, ::step_x]

    if is_complex:
        kspace = sample
        image = np.abs(np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace))))
    else:
        image = sample
        kspace = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image))))

    if np.all(np.isfinite(image)):
        image_low, image_high = np.percentile(image, [1.0, 99.0])
        if image_high > image_low:
            score += 0.8
            reasons.append("reconstructable")

    cy, cx = kspace.shape[0] // 2, kspace.shape[1] // 2
    radius_y = max(2, kspace.shape[0] // 16)
    radius_x = max(2, kspace.shape[1] // 16)
    center_energy = float(np.sum(np.abs(
        kspace[
            max(0, cy-radius_y):min(kspace.shape[0], cy+radius_y+1),
            max(0, cx-radius_x):min(kspace.shape[1], cx+radius_x+1),
        ]
    )))
    total_energy = float(np.sum(np.abs(kspace))) + 1e-12
    center_ratio = center_energy / total_energy
    if 0.002 <= center_ratio <= 0.95:
        score += 1.0
        reasons.append("MRI-like frequency distribution")

    fus_likeness, fus_reason = _fus_image_likeness(magnitude)
    if not is_complex:
        if fus_likeness >= 0.70:
            score += 4.0 + min((fus_likeness - 0.70) * 6.0, 1.8)
            reasons.append("strong FUS image-likeness")
        elif fus_likeness >= 0.45:
            score += 1.8
            reasons.append("moderate FUS image-likeness")
        elif fus_likeness < 0.10:
            score -= 1.5
            reasons.append("weak adjacent-pixel continuity")
    else:
        score += max(fus_likeness, 0.0) * 0.25

    reasons.append(fus_reason)
    return score, ", ".join(reasons), fus_likeness


def _candidate_from_cache(path: Path, profile: dict) -> Optional[_Candidate]:
    try:
        dtype = np.dtype(profile["dtype"])
        return _Candidate(
            rows=int(profile["rows"]),
            cols=int(profile["cols"]),
            dtype=dtype,
            dtype_name=str(profile["dtype_name"]),
            endian_name=str(profile["endian_name"]),
            offset=int(profile.get("offset", 0)),
            is_complex=bool(profile.get("is_complex", False)),
        )
    except Exception:
        return None


def _experimental_offsets(file_size: int) -> list[int]:
    offsets = {
        0, 2, 4, 8, 16, 32, 64, 96, 128, 192, 256, 384, 512,
        768, 1024, 1536, 2048, 3072, 4096, 6144, 8192, 12288,
        16384, 24576, 32768, 65536,
    }
    for bytes_per_pixel in (2, 4, 8):
        for side in (
            64, 96, 128, 160, 192, 224, 240, 256, 288, 320,
            384, 448, 480, 512, 576, 640, 768, 896, 1024,
        ):
            offset = file_size - side * side * bytes_per_pixel
            if 0 <= offset < file_size:
                offsets.add(offset)
    return sorted(value for value in offsets if 0 <= value < file_size)


def _experimental_shapes(element_count: int) -> list[tuple[int, int]]:
    shapes = set(_matrix_shapes(element_count))
    dimensions = tuple(range(64, 1025, 16))
    for rows in dimensions:
        if element_count % rows:
            continue
        cols = element_count // rows
        if 32 <= cols <= 4096:
            ratio = max(rows, cols) / max(min(rows, cols), 1)
            if ratio <= 12.0:
                shapes.add((rows, cols))
    return sorted(
        shapes,
        key=lambda rc: (
            abs(np.log(max(rc) / max(min(rc), 1))),
            abs(rc[0] - rc[1]),
        ),
    )[:120]


def load_raw_file_experimental(path: Path) -> RawImportResult:
    """Generate a labelled preview when the exact RAW format is unknown."""
    path = Path(path)
    file_size = path.stat().st_size
    candidates = []

    interpretations = [
        (np.dtype("<u2"), "Unsigned Int16", "Little Endian", False),
        (np.dtype("<i2"), "Signed Int16", "Little Endian", False),
        (np.dtype(">u2"), "Unsigned Int16", "Big Endian", False),
        (np.dtype(">i2"), "Signed Int16", "Big Endian", False),
        (np.dtype("<f4"), "Float32", "Little Endian", False),
        (np.dtype(">f4"), "Float32", "Big Endian", False),
        (np.dtype("<c8"), "Complex Float32", "Little Endian", True),
        (np.dtype(">c8"), "Complex Float32", "Big Endian", True),
    ]

    for offset in _experimental_offsets(file_size):
        payload = file_size - offset
        for dtype, dtype_name, endian_name, is_complex in interpretations:
            if payload % dtype.itemsize:
                continue
            element_count = payload // dtype.itemsize
            for rows, cols in _experimental_shapes(element_count):
                count = rows * cols
                try:
                    values = np.fromfile(
                        path,
                        dtype=dtype,
                        offset=offset,
                        count=count,
                    )
                    if values.size != count:
                        continue
                    array = values.reshape(rows, cols)
                    score, reason, likeness = _score_candidate(
                        array,
                        is_complex,
                    )
                except Exception:
                    continue

                if rows == cols:
                    score += 0.25
                score -= min(offset / max(file_size, 1), 0.4)

                candidates.append({
                    "score": float(score),
                    "rows": int(rows),
                    "cols": int(cols),
                    "dtype_name": dtype_name,
                    "endian_name": endian_name,
                    "offset": int(offset),
                    "is_complex": bool(is_complex),
                    "array": array,
                    "likeness": float(likeness),
                    "reason": reason,
                })

    if not candidates:
        raise RawImportError(
            "No exact or experimental RAW preview candidate was found."
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    best = candidates[0]

    if best["is_complex"]:
        display = np.abs(
            np.fft.fftshift(
                np.fft.ifft2(np.fft.ifftshift(best["array"]))
            )
        )
    else:
        display = np.asarray(best["array"], dtype=float)

    finite = display[np.isfinite(display)]
    low, high = np.percentile(finite, [1.0, 99.0])
    if high > low:
        display = np.clip((display - low) / (high - low), 0.0, 1.0)
    else:
        display = np.zeros_like(display, dtype=float)

    summary = " | ".join(
        f"{item['rows']}×{item['cols']} {item['dtype_name']} "
        f"offset {item['offset']} score {item['score']:.3f}"
        for item in candidates[:3]
    )

    return RawImportResult(
        path=path,
        data=np.asarray(display, dtype=np.float32),
        rows=best["rows"],
        cols=best["cols"],
        dtype_name=best["dtype_name"],
        endian_name=best["endian_name"],
        offset_bytes=best["offset"],
        is_kspace=False,
        confidence=float(
            np.clip(0.35 + max(best["likeness"], 0.0) * 0.45, 0.15, 0.89)
        ),
        reason="Experimental RAW preview; " + best["reason"],
        recommended_display="Direct Array",
        fus_image_likeness=max(best["likeness"], 0.0),
        experimental=True,
        candidate_summary=summary,
    )


def load_raw_file_auto(
    path: Path,
    cache_path: Optional[Path] = None,
    minimum_confidence: float = 0.56,
) -> RawImportResult:
    path = Path(path)
    if not path.exists() or not path.is_file():
        raise RawImportError(f"RAW file does not exist: {path}")

    file_size = path.stat().st_size
    if file_size < 128:
        raise RawImportError("File is too small to be a supported RAW image.")

    # First use the exact, proven FUS Investigation Replay decoder.
    exact_result = try_render_fus_raw_exact(path)
    if exact_result is not None:
        return exact_result

    cache = _safe_cache_read(cache_path)
    key = _profile_key(path)
    cached = _candidate_from_cache(path, cache.get(key, {}))
    candidates: list[_Candidate] = []

    if cached is not None:
        candidates.append(cached)

    for offset in _OFFSETS:
        if offset >= file_size:
            continue
        payload = file_size - offset

        for dtype, dtype_name, endian_name, is_complex in _dtype_candidates():
            item_size = dtype.itemsize
            if dtype_name == "Complex Int16":
                denominator = item_size * 2
            else:
                denominator = item_size
            if payload % denominator != 0:
                continue

            element_count = payload // denominator
            for rows, cols in _matrix_shapes(element_count):
                candidates.append(_Candidate(
                    rows=rows,
                    cols=cols,
                    dtype=dtype,
                    dtype_name=dtype_name,
                    endian_name=endian_name,
                    offset=offset,
                    is_complex=is_complex,
                ))

    # Remove duplicates while preserving cached candidate priority.
    unique: list[_Candidate] = []
    seen = set()
    for candidate in candidates:
        marker = (
            candidate.rows, candidate.cols, candidate.dtype.str,
            candidate.dtype_name, candidate.offset,
        )
        if marker not in seen:
            seen.add(marker)
            unique.append(candidate)

    if not unique:
        return load_raw_file_experimental(path)

    evaluated: list[tuple[_Candidate, np.ndarray]] = []
    for candidate in unique[:320]:
        try:
            array = _decode_candidate(path, candidate)
            score, reason, fus_likeness = _score_candidate(
                array, candidate.is_complex
            )
            # Prefer common square MRI matrices and smaller header offsets.
            if candidate.rows == candidate.cols:
                score += 0.35
            if candidate.rows in _COMMON_DIMS and candidate.cols in _COMMON_DIMS:
                score += 0.20
            score -= candidate.offset / max(file_size, 1) * 0.4
            candidate.score = score
            candidate.reason = reason
            candidate.fus_image_likeness = fus_likeness
            evaluated.append((candidate, array))
        except Exception:
            continue

    if not evaluated:
        return load_raw_file_experimental(path)

    evaluated.sort(key=lambda item: item[0].score, reverse=True)
    best, best_array = evaluated[0]
    second_score = evaluated[1][0].score if len(evaluated) > 1 else best.score - 3.0

    absolute = 1.0 / (1.0 + math.exp(-(best.score - 2.0)))
    separation = 1.0 / (1.0 + math.exp(-(best.score - second_score)))
    confidence = float(np.clip(0.65 * absolute + 0.35 * separation, 0.0, 1.0))

    if confidence < minimum_confidence:
        return load_raw_file_experimental(path)


    cache[key] = {
        "rows": best.rows,
        "cols": best.cols,
        "dtype": best.dtype.str,
        "dtype_name": best.dtype_name,
        "endian_name": best.endian_name,
        "offset": best.offset,
        "is_complex": best.is_complex,
    }
    _safe_cache_write(cache_path, cache)

    return RawImportResult(
        path=path,
        data=best_array,
        rows=best.rows,
        cols=best.cols,
        dtype_name=best.dtype_name,
        endian_name=best.endian_name,
        offset_bytes=best.offset,
        is_kspace=best.is_complex,
        confidence=confidence,
        reason=best.reason or "Best automatic RAW interpretation",
        recommended_display=(
            "Direct Array"
            if (not best.is_complex and best.fus_image_likeness >= 0.45)
            else ("Reconstructed Image" if best.is_complex else "Auto")
        ),
        fus_image_likeness=max(float(best.fus_image_likeness), 0.0),
    )
