from __future__ import annotations

import math
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


ASCII_RE = re.compile(rb"[\x20-\x7e]{4,}")


@dataclass(slots=True)
class NumericCandidate:
    dtype: str
    offset: int
    count: int
    finite_ratio: float
    nonzero_ratio: float
    nonnegative_ratio: float
    dynamic_ratio: float
    smoothness: float
    spectral_likeness: float
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class BinaryProfile:
    path: str
    size_bytes: int
    ascii_strings: list[str]
    repeated_periods: list[dict]
    numeric_candidates: list[NumericCandidate]
    byte_entropy: float
    zero_ratio: float

    def to_dict(self) -> dict:
        result = asdict(self)
        result["numeric_candidates"] = [item.to_dict() for item in self.numeric_candidates]
        return result


class BinaryProbe:
    """Conservative binary profiler.

    It does not claim a decoded format. It ranks plausible numeric regions and
    records evidence needed to compare SpectrumMsg and Acquisition containers.
    """

    DTYPES = ("<f4", ">f4", "<f8", ">f8", "<i2", ">i2", "<u2", ">u2")
    WINDOW_COUNTS = (256, 512, 1024, 2048, 4096)
    MAX_BYTES = 32 * 1024 * 1024

    def profile(self, path: Path) -> BinaryProfile:
        data = path.read_bytes()[: self.MAX_BYTES]
        return BinaryProfile(
            path=str(path),
            size_bytes=path.stat().st_size,
            ascii_strings=self._ascii_strings(data),
            repeated_periods=self._periodicity(data),
            numeric_candidates=self._numeric_candidates(data),
            byte_entropy=self._entropy(data),
            zero_ratio=(data.count(0) / len(data)) if data else 0.0,
        )

    @staticmethod
    def _ascii_strings(data: bytes) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for match in ASCII_RE.finditer(data):
            text = match.group().decode("ascii", errors="ignore").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            values.append(text[:240])
            if len(values) >= 80:
                break
        return values

    @staticmethod
    def _entropy(data: bytes) -> float:
        if not data:
            return 0.0
        counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(np.float64)
        probs = counts[counts > 0] / len(data)
        return float(-np.sum(probs * np.log2(probs)))

    def _periodicity(self, data: bytes) -> list[dict]:
        if len(data) < 2048:
            return []
        sample = np.frombuffer(data[: min(len(data), 4 * 1024 * 1024)], dtype=np.uint8).astype(np.float64)
        sample -= sample.mean()
        periods: list[dict] = []
        for period in (64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384):
            if period * 3 >= len(sample):
                continue
            a = sample[:-period]
            b = sample[period:]
            denom = float(np.linalg.norm(a) * np.linalg.norm(b))
            corr = float(np.dot(a, b) / denom) if denom else 0.0
            periods.append({"period_bytes": period, "correlation": round(corr, 6)})
        return sorted(periods, key=lambda item: item["correlation"], reverse=True)[:8]

    def _numeric_candidates(self, data: bytes) -> list[NumericCandidate]:
        results: list[NumericCandidate] = []
        offsets = self._candidate_offsets(data)
        for dtype in self.DTYPES:
            itemsize = np.dtype(dtype).itemsize
            for offset in offsets:
                aligned = offset - (offset % itemsize)
                for count in self.WINDOW_COUNTS:
                    byte_count = count * itemsize
                    if aligned < 0 or aligned + byte_count > len(data):
                        continue
                    try:
                        with np.errstate(all="ignore"):
                            raw = np.frombuffer(data, dtype=dtype, count=count, offset=aligned)
                            values = raw.astype(np.float64)
                    except (ValueError, TypeError, FloatingPointError):
                        continue
                    candidate = self._score(dtype, aligned, values)
                    if candidate.score >= 30.0:
                        results.append(candidate)
        results.sort(key=lambda item: item.score, reverse=True)
        deduped: list[NumericCandidate] = []
        for item in results:
            if any(existing.dtype == item.dtype and abs(existing.offset - item.offset) < 32 for existing in deduped):
                continue
            deduped.append(item)
            if len(deduped) >= 40:
                break
        return deduped

    @staticmethod
    def _candidate_offsets(data: bytes) -> list[int]:
        offsets = {0, 4, 8, 16, 24, 32, 48, 64, 96, 128, 256, 512, 1024, 2048, 4096, 8192}
        for match in ASCII_RE.finditer(data[: min(len(data), 2 * 1024 * 1024)]):
            offsets.add(match.start())
            offsets.add(match.end())
            for delta in (4, 8, 16, 32, 64, 128):
                offsets.add(match.end() + delta)
        if data:
            for fraction in (0.1, 0.2, 0.25, 0.33, 0.5, 0.66, 0.75, 0.9):
                offsets.add(int(len(data) * fraction))
        return sorted(offset for offset in offsets if 0 <= offset < len(data))

    @staticmethod
    def _score(dtype: str, offset: int, values: np.ndarray) -> NumericCandidate:
        finite = np.isfinite(values)
        finite_ratio = float(np.mean(finite))
        clean = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
        abs_values = np.abs(clean)
        nonzero_ratio = float(np.mean(abs_values > 1e-20))
        nonnegative_ratio = float(np.mean(clean >= 0))
        median = float(np.median(abs_values))
        p95 = float(np.percentile(abs_values, 95))
        dynamic_ratio = p95 / max(median, 1e-20)
        # Clip extreme reinterpretations before variance calculations. This
        # prevents random byte patterns decoded as Float64 from overflowing.
        bounded = np.clip(clean, -1e100, 1e100)
        diffs = np.diff(bounded)
        with np.errstate(all="ignore"):
            base_std = float(np.nanstd(bounded))
            diff_std = float(np.nanstd(diffs))
        if not math.isfinite(base_std) or not math.isfinite(diff_std):
            smoothness = 0.0
        else:
            smoothness = 1.0 - min(1.0, diff_std / max(base_std * 2.0, 1e-20))
        # A spectrum-like sequence is mostly finite/nonnegative, not constant,
        # and has sparse peaks above a smoother baseline.
        peak_fraction = float(np.mean(abs_values >= max(p95, 1e-20)))
        spectral_likeness = (
            0.35 * finite_ratio
            + 0.20 * nonzero_ratio
            + 0.15 * nonnegative_ratio
            + 0.15 * min(1.0, math.log10(max(dynamic_ratio, 1.0)) / 3.0)
            + 0.10 * smoothness
            + 0.05 * (1.0 - min(1.0, peak_fraction * 20.0))
        )
        score = 100.0 * spectral_likeness
        return NumericCandidate(
            dtype=dtype,
            offset=offset,
            count=len(values),
            finite_ratio=round(finite_ratio, 6),
            nonzero_ratio=round(nonzero_ratio, 6),
            nonnegative_ratio=round(nonnegative_ratio, 6),
            dynamic_ratio=round(dynamic_ratio, 6),
            smoothness=round(smoothness, 6),
            spectral_likeness=round(spectral_likeness, 6),
            score=round(score, 3),
        )
