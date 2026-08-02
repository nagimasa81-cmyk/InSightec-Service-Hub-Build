from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import numpy as np

_TIME_RE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}):(?P<ms>\d{3})")
_START_RE = re.compile(r"(?:Got\s+StartSpectrumMeasurementA|StartSpectrumMeasurement:\s*SetInitial\s+PowerRatios)", re.I)
_SET_RE = re.compile(r"AblPowerRatio\s*=\s*(?P<ratio>[-+0-9.eE]+)", re.I)
_SCORE_RE = re.compile(
    r"Calculated Energy:\s*<(?P<energy>[-+0-9.eE]+)>.*?"
    r"(?:Bottom Limit Of Harmless Energy|Bottom Energy limit)\s*[:=]\s*<(?P<limit>[-+0-9.eE]+)>",
    re.I,
)
_STOP_RE = re.compile(r"StopSpectrumMeasurement|Spectrum Measurement.*(?:stop|finished)", re.I)


@dataclass(slots=True)
class AcousticControlSample:
    elapsed_s: float
    power_percent: float | None = None
    score_percent: float | None = None
    energy: float | None = None
    harmless_limit: float | None = None


@dataclass(slots=True)
class AcousticControlSegment:
    source: Path
    start_clock_s: float
    samples: list[AcousticControlSample] = field(default_factory=list)


@dataclass(slots=True)
class AcousticControlTrend:
    time_s: np.ndarray
    power_percent: np.ndarray
    score_percent: np.ndarray
    energy: np.ndarray
    harmless_limit: np.ndarray
    source: Path | None = None
    segment_index: int | None = None
    status: str = "Unavailable"
    acoustic_onset_raw_s: float | None = None
    cavitation_event_s: float | None = None
    modulation_event_s: tuple[float, ...] = ()


class AcousticControlService:
    """Read the workstation cavitation-control telemetry from Acquisition logs.

    Verified from supplied ANx cases:
    * ``AblPowerRatio`` is the applied/requested power ratio (1.0 = 100%).
    * The displayed cavitation score follows the normalized control energy:
      ``Calculated Energy / Bottom Limit Of Harmless Energy * 100``.

    Values are paired by timestamp and are never synthesized from spectrum peaks.
    """

    def find_log(self, workspace: Path) -> Path | None:
        candidates = sorted(
            workspace.rglob("Acquisition_Brain_*.txt"),
            key=lambda p: (p.stat().st_size, str(p)),
            reverse=True,
        )
        return candidates[0] if candidates else None

    @staticmethod
    def _clock_seconds(line: str) -> float | None:
        match = _TIME_RE.search(line)
        if not match:
            return None
        return (
            int(match.group("h")) * 3600
            + int(match.group("m")) * 60
            + int(match.group("s"))
            + int(match.group("ms")) / 1000.0
        )

    def parse_segments(self, path: Path) -> list[AcousticControlSegment]:
        segments: list[AcousticControlSegment] = []
        current: AcousticControlSegment | None = None
        latest_power: float | None = None
        latest_score: tuple[float, float, float] | None = None

        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for line in stream:
                clock = self._clock_seconds(line)
                if _START_RE.search(line) and clock is not None:
                    # Workstation writes several start-related lines for one sonication.
                    # Debounce them so one physical sonication becomes one telemetry segment.
                    if current is not None and (clock - current.start_clock_s) < 2.0:
                        continue
                    current = AcousticControlSegment(path, clock)
                    segments.append(current)
                    latest_power = None
                    latest_score = None
                    continue
                if current is None or clock is None:
                    continue
                if _STOP_RE.search(line) and current.samples:
                    current = None
                    continue

                power_match = _SET_RE.search(line)
                score_match = _SCORE_RE.search(line)
                if power_match:
                    latest_power = float(power_match.group("ratio")) * 100.0
                if score_match:
                    energy = float(score_match.group("energy"))
                    limit = float(score_match.group("limit"))
                    score = energy / limit * 100.0 if limit > 0 else np.nan
                    latest_score = (score, energy, limit)

                if power_match or score_match:
                    elapsed = clock - current.start_clock_s
                    if elapsed < -12 * 3600:  # midnight rollover
                        elapsed += 24 * 3600
                    score, energy, limit = latest_score or (None, None, None)
                    current.samples.append(
                        AcousticControlSample(
                            elapsed_s=max(0.0, elapsed),
                            power_percent=latest_power,
                            score_percent=score,
                            energy=energy,
                            harmless_limit=limit,
                        )
                    )
        return [segment for segment in segments if segment.samples]

    @staticmethod
    def _collapse(samples: list[AcousticControlSample]) -> tuple[np.ndarray, ...]:
        # Logs often contain a power line and score line a few ms apart. Retain the
        # latest value and sort; interpolation then gives one coherent WS trace.
        ordered = sorted(samples, key=lambda sample: sample.elapsed_s)
        t = np.asarray([sample.elapsed_s for sample in ordered], dtype=float)
        power = np.asarray([
            sample.power_percent if sample.power_percent is not None else np.nan
            for sample in ordered
        ], dtype=float)
        score = np.asarray([
            sample.score_percent if sample.score_percent is not None else np.nan
            for sample in ordered
        ], dtype=float)
        energy = np.asarray([
            sample.energy if sample.energy is not None else np.nan
            for sample in ordered
        ], dtype=float)
        limit = np.asarray([
            sample.harmless_limit if sample.harmless_limit is not None else np.nan
            for sample in ordered
        ], dtype=float)
        return t, power, score, energy, limit

    @staticmethod
    def _fill_forward(values: np.ndarray) -> np.ndarray:
        result = values.copy()
        last = np.nan
        for index, value in enumerate(result):
            if np.isfinite(value):
                last = value
            elif np.isfinite(last):
                result[index] = last
        return result

    @staticmethod
    def _treatment_segment_index(workspace: Path, sonication_index: int, segment_count: int) -> int:
        """Map exported Sonication folders to the matching Acquisition segment.

        A treatment export can contain DQA/calibration spectrum measurements before
        the treatment Sonication folders.  The supplied treatment contains 15
        Acquisition segments but only 8 Sonication folders; the treatment replay is
        therefore the final eight segments, not the first eight.
        """
        sonication_count = len([
            path for path in workspace.iterdir()
            if path.is_dir() and re.fullmatch(r"Sonication\d+", path.name, re.I)
        ])
        if sonication_count <= 0 or segment_count <= sonication_count:
            return max(0, min(sonication_index, segment_count - 1))
        offset = segment_count - sonication_count
        return max(0, min(offset + sonication_index, segment_count - 1))

    def measured_duration_for_sonication(self, workspace: Path, sonication_index: int) -> float | None:
        log = self.find_log(workspace)
        if log is None:
            return None
        segments = self.parse_segments(log)
        if not segments:
            return None
        index = self._treatment_segment_index(workspace, sonication_index, len(segments))
        samples = segments[index].samples
        if not samples:
            return None
        values = [sample.elapsed_s for sample in samples]
        return max(0.0, float(max(values) - min(values)))

    @staticmethod
    def _detect_acoustic_onset(t: np.ndarray, power: np.ndarray) -> float:
        """Return the measured start of the acoustic power ramp.

        Acquisition telemetry begins several seconds before energy delivery.
        The old normalized mapping incorrectly stretched that pre-roll across the
        complete MR replay.  Onset is the first sustained departure from the
        initial power-ratio baseline.
        """
        valid = np.isfinite(t) & np.isfinite(power)
        if not valid.any():
            return float(np.nanmin(t)) if t.size else 0.0
        tv = t[valid]; pv = power[valid]
        baseline_count = max(3, min(len(pv), 50))
        baseline = float(np.nanmedian(pv[:baseline_count]))
        threshold = max(0.5, abs(baseline) * 0.02)
        changed = np.flatnonzero(np.abs(pv - baseline) >= threshold)
        if changed.size:
            return float(tv[int(changed[0])])
        return float(tv[0])

    @staticmethod
    def _event_times(t: np.ndarray, power: np.ndarray, score: np.ndarray) -> tuple[float | None, tuple[float, ...]]:
        cavitation = None
        valid_score = np.isfinite(score)
        if valid_score.any():
            indices = np.flatnonzero(valid_score & (score >= 40.0))
            if indices.size:
                cavitation = float(t[int(indices[0])])
        modulations: list[float] = []
        for i in range(1, len(power)):
            if np.isfinite(power[i-1]) and np.isfinite(power[i]) and power[i-1] - power[i] >= 8.0:
                candidate = float(t[i])
                if not modulations or candidate - modulations[-1] >= 0.10:
                    modulations.append(candidate)
        return cavitation, tuple(modulations)

    def trend_for_sonication(
        self,
        workspace: Path,
        sonication_index: int,
        replay_count: int,
        replay_duration_s: float,
    ) -> AcousticControlTrend:
        empty = np.full(max(replay_count, 1), np.nan, dtype=float)
        target_t = np.linspace(0.0, max(replay_duration_s, 0.0), max(replay_count, 1))
        log = self.find_log(workspace)
        if log is None:
            return AcousticControlTrend(target_t, empty.copy(), empty.copy(), empty.copy(), empty.copy())
        segments = self.parse_segments(log)
        if not segments:
            return AcousticControlTrend(target_t, empty.copy(), empty.copy(), empty.copy(), empty.copy(), source=log)
        index = self._treatment_segment_index(workspace, sonication_index, len(segments))
        segment = segments[index]
        t, power, score, energy, limit = self._collapse(segment.samples)
        if t.size == 0:
            return AcousticControlTrend(target_t, empty.copy(), empty.copy(), empty.copy(), empty.copy(), source=log, segment_index=index)

        onset_raw = self._detect_acoustic_onset(t, power)
        # Keep the Acquisition segment clock.  The chart starts at MR acquisition
        # start, so the pre-sonication MR frames remain visible and the acoustic
        # ramp appears at its measured offset instead of being forced to t=0.
        source_t = np.maximum(t - float(np.nanmin(t)), 0.0)

        # Preserve measured Acquisition time and place it on the complete MR
        # acquisition timeline.  Never stretch one sonication to fill the chart.
        def resample(values: np.ndarray) -> np.ndarray:
            values = self._fill_forward(values)
            valid = np.isfinite(values) & np.isfinite(source_t)
            if not valid.any():
                return empty.copy()
            if valid.sum() == 1:
                result = np.full(target_t.shape, np.nan, dtype=float)
                result[target_t >= source_t[valid][0]] = values[valid][0]
                return result
            return np.interp(target_t, source_t[valid], values[valid], left=np.nan, right=values[valid][-1])

        sampled_power = resample(power)
        sampled_score = resample(score)
        sampled_energy = resample(energy)
        sampled_limit = resample(limit)
        cavitation, modulations = self._event_times(target_t, sampled_power, sampled_score)
        return AcousticControlTrend(
            target_t, sampled_power, sampled_score, sampled_energy, sampled_limit,
            source=log, segment_index=index,
            status=f"MR-start timeline; acoustic onset +{onset_raw:.3f} s; Acquisition segment {index + 1}/{len(segments)}",
            acoustic_onset_raw_s=onset_raw, cavitation_event_s=cavitation, modulation_event_s=modulations,
        )

