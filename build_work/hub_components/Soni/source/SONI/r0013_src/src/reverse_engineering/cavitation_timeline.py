from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import csv
import json
import re

import numpy as np

from src.services.acoustic_control_service import AcousticControlService

_TIME_RE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})[:.](?P<ms>\d{3})")
_KEYWORDS = {
    "cavitation": re.compile(r"cavitat|bubble|broadband|subharm|ultraharm", re.I),
    "modulation": re.compile(r"modulat|reduce(?:d|s|ing)?\s+power|power\s+reduction|power\s+was\s+(?:decreased|limited)", re.I),
    "stop": re.compile(r"abort(?:ed|ing)?\s+sonication|stopsonication|stopping\s+sonication|sonication\s+(?:was|is)\s+stopped|terminate(?:d|ing)?\s+sonication", re.I),
    "safety": re.compile(r"\s(?:Wrn|Err|Sev|Ftl)\s.*(?:cavitat|sonicat|power|interlock|fault|failure)", re.I),
}


@dataclass(slots=True)
class TimelineEvent:
    elapsed_s: float
    clock_s: float
    category: str
    source: str
    message: str


@dataclass(slots=True)
class CavitationTimeline:
    sonication_number: int
    start_clock_s: float
    duration_s: float
    time_s: list[float] = field(default_factory=list)
    power_percent: list[float] = field(default_factory=list)
    score_percent: list[float] = field(default_factory=list)
    energy: list[float] = field(default_factory=list)
    harmless_limit: list[float] = field(default_factory=list)
    events: list[TimelineEvent] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["events"] = [asdict(event) for event in self.events]
        return data


class CavitationTimelineAnalyzer:
    """Build an evidence-only common timeline for one sonication.

    Absolute workstation clock is used to join Acquisition, Safety, HwServer,
    CSA, and error logs. No MR-temperature shift or synthetic delay is applied.
    """

    def __init__(self) -> None:
        self.acoustic = AcousticControlService()

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

    def analyze(self, workspace: Path, sonication_number: int) -> CavitationTimeline:
        workspace = workspace.resolve()
        log = self.acoustic.find_log(workspace)
        if log is None:
            raise FileNotFoundError("Acquisition_Brain telemetry was not found")
        segments = self.acoustic.parse_segments(log)
        if not segments:
            raise ValueError("No sonication telemetry segments were parsed")
        index = max(0, min(sonication_number - 1, len(segments) - 1))
        segment = segments[index]
        samples = sorted(segment.samples, key=lambda sample: sample.elapsed_s)
        start = float(segment.start_clock_s)
        duration = max((sample.elapsed_s for sample in samples), default=0.0)
        margin_before = 1.0
        margin_after = 2.0

        events: list[TimelineEvent] = []
        seen_events: set[tuple[int, str, str, str]] = set()
        log_candidates = [
            path for path in workspace.rglob("*.txt")
            if any(token in path.name.lower() for token in ("safety", "acquisition", "hwserver", "err_", "csa_", "cavitation"))
        ]
        for path in sorted(log_candidates):
            try:
                with path.open("r", encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        clock = self._clock_seconds(line)
                        if clock is None:
                            continue
                        elapsed = clock - start
                        if elapsed < -12 * 3600:
                            elapsed += 24 * 3600
                        if not (-margin_before <= elapsed <= duration + margin_after):
                            continue
                        category = next((name for name, rx in _KEYWORDS.items() if rx.search(line)), None)
                        if category is None:
                            continue
                        message=line.strip()[:1000]
                        signature=(int(round(elapsed * 1000.0)), category, path.name, message)
                        if signature in seen_events:
                            continue
                        seen_events.add(signature)
                        events.append(TimelineEvent(
                            elapsed_s=float(elapsed),
                            clock_s=float(clock),
                            category=category,
                            source=path.name,
                            message=message,
                        ))
            except OSError:
                continue

        events.sort(key=lambda event: (event.elapsed_s, event.source, event.message))
        timeline = CavitationTimeline(
            sonication_number=index + 1,
            start_clock_s=start,
            duration_s=float(duration),
            time_s=[float(sample.elapsed_s) for sample in samples],
            power_percent=[float(sample.power_percent) if sample.power_percent is not None else float("nan") for sample in samples],
            score_percent=[float(sample.score_percent) if sample.score_percent is not None else float("nan") for sample in samples],
            energy=[float(sample.energy) if sample.energy is not None else float("nan") for sample in samples],
            harmless_limit=[float(sample.harmless_limit) if sample.harmless_limit is not None else float("nan") for sample in samples],
            events=events,
        )
        timeline.findings = self._findings(timeline)
        return timeline

    @staticmethod
    def _findings(timeline: CavitationTimeline) -> list[str]:
        findings: list[str] = []
        t = np.asarray(timeline.time_s, dtype=float)
        p = np.asarray(timeline.power_percent, dtype=float)
        s = np.asarray(timeline.score_percent, dtype=float)
        valid_p = np.isfinite(p)
        valid_s = np.isfinite(s)
        if valid_p.any():
            peak_index = int(np.nanargmax(p))
            findings.append(f"Peak Power {p[peak_index]:.2f}% at {t[peak_index]:.3f}s")
            # A sustained drop after a higher command is evidence of modulation/reduction.
            running_peak = np.maximum.accumulate(np.where(valid_p, p, -np.inf))
            drop = running_peak - p
            candidates = np.where(valid_p & (drop >= 5.0))[0]
            if candidates.size:
                i = int(candidates[0])
                findings.append(f"Power reduction candidate at {t[i]:.3f}s: {running_peak[i]:.2f}% -> {p[i]:.2f}%")
        if valid_s.any():
            peak_index = int(np.nanargmax(s))
            findings.append(f"Peak Score {s[peak_index]:.2f}% at {t[peak_index]:.3f}s")
            high = np.where(valid_s & (s >= 50.0))[0]
            if high.size:
                findings.append(f"Score first crossed 50% at {t[int(high[0])]:.3f}s")
        stop_events = [event for event in timeline.events if event.category == "stop"]
        modulation_events = [event for event in timeline.events if event.category == "modulation"]
        if modulation_events:
            findings.append(f"{len(modulation_events)} modulation/power-control log events found in the sonication window")
        if stop_events:
            findings.append(f"{len(stop_events)} stop/abort log events found in the sonication window")
        if not timeline.events:
            findings.append("No keyword-matched control/safety events found; inspect raw log window manually")
        return findings

    @staticmethod
    def export(timeline: CavitationTimeline, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"sonication_{timeline.sonication_number}_cavitation_timeline.json").write_text(
            json.dumps(timeline.to_dict(), indent=2, ensure_ascii=False, allow_nan=True), encoding="utf-8"
        )
        with (output_dir / f"sonication_{timeline.sonication_number}_telemetry.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["elapsed_s", "power_percent", "score_percent", "energy", "harmless_limit"])
            for row in zip(timeline.time_s, timeline.power_percent, timeline.score_percent, timeline.energy, timeline.harmless_limit):
                writer.writerow(row)
        with (output_dir / f"sonication_{timeline.sonication_number}_events.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["elapsed_s", "clock_s", "category", "source", "message"])
            for event in timeline.events:
                writer.writerow([event.elapsed_s, event.clock_s, event.category, event.source, event.message])
