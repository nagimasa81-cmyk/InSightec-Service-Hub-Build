from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np

from src.reverse_engineering.binary_probe import BinaryProbe, BinaryProfile
from src.services.acoustic_control_service import AcousticControlService
from src.services.sonication_channel_service import SonicationChannelService
from src.services.sonication_frequency_service import SonicationFrequencyService


@dataclass(slots=True)
class FileEvidence:
    path: str
    family: str
    sonication: str | None
    main_frequency_hz: float | None
    configured_channel: int | None
    profile: dict
    interpretation: str
    confidence: str


@dataclass(slots=True)
class TelemetryEvidence:
    path: str
    segment_count: int
    sample_count: int
    power_min: float | None
    power_max: float | None
    score_min: float | None
    score_max: float | None


@dataclass(slots=True)
class ReverseEngineeringReport:
    generated_at: str
    root: str
    files: list[FileEvidence] = field(default_factory=list)
    telemetry: list[TelemetryEvidence] = field(default_factory=list)
    conclusions: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "root": self.root,
            "files": [asdict(item) for item in self.files],
            "telemetry": [asdict(item) for item in self.telemetry],
            "conclusions": self.conclusions,
        }


class HydrophoneReverseEngineeringLab:
    """Evidence-first analyzer for proprietary hydrophone exports.

    The lab deliberately avoids feeding speculative decodes into Replay. It
    produces a report labelled Confirmed/Estimated/Unknown so display code can
    only consume evidence after explicit promotion.
    """

    SONICATION_RE = re.compile(r"sonication\s*[_-]?(\d+)", re.I)

    def __init__(self) -> None:
        self.probe = BinaryProbe()
        self.telemetry_service = AcousticControlService()
        self.frequency_service = SonicationFrequencyService()
        self.channel_service = SonicationChannelService()

    def analyze(self, root: Path, output_dir: Path | None = None) -> ReverseEngineeringReport:
        root = root.expanduser().resolve()
        output_dir = (output_dir or (root / "Hydrophone_RE_Report")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        report = ReverseEngineeringReport(
            generated_at=datetime.now().isoformat(timespec="seconds"),
            root=str(root),
        )

        candidates = sorted(
            (path for path in root.rglob("*") if path.is_file() and self._is_candidate(path)),
            key=lambda path: str(path).lower(),
        )
        for path in candidates:
            if path.suffix.lower() in {".txt", ".log"} and "acquisition_brain" in path.name.lower():
                report.telemetry.append(self._analyze_telemetry(path))
                continue
            profile = self.probe.profile(path)
            son_folder = self._sonication_folder(path)
            freq = self.frequency_service.read(son_folder) if son_folder else None
            channel = self.channel_service.read(son_folder) if son_folder else None
            family = self._family(path)
            interpretation, confidence = self._interpret(profile, family)
            report.files.append(FileEvidence(
                path=str(path),
                family=family,
                sonication=son_folder.name if son_folder else None,
                main_frequency_hz=freq.frequency_hz if freq else None,
                configured_channel=channel.channel if channel else None,
                profile=profile.to_dict(),
                interpretation=interpretation,
                confidence=confidence,
            ))

        report.conclusions = self._build_conclusions(report)
        self._write_outputs(report, output_dir)
        return report

    @staticmethod
    def _is_candidate(path: Path) -> bool:
        low = path.name.lower()
        return (
            path.suffix.lower() == ".dmp"
            and ("spectrummsg" in low or "acquisition" in low or "reflection" in low or "cavitation" in low)
        ) or (path.suffix.lower() in {".txt", ".log"} and "acquisition_brain" in low)

    @staticmethod
    def _family(path: Path) -> str:
        low = path.name.lower()
        if "spectrummsg" in low:
            return "SpectrumMsg"
        if "acquisition" in low:
            return "Acquisition"
        if "reflection" in low:
            return "Reflection"
        if "cavitation" in low:
            return "CavitationControl"
        return "Unknown"

    def _sonication_folder(self, path: Path) -> Path | None:
        for parent in (path.parent, *path.parents):
            if self.SONICATION_RE.search(parent.name):
                return parent
        return None

    def _analyze_telemetry(self, path: Path) -> TelemetryEvidence:
        segments = self.telemetry_service.parse_segments(path)
        samples = [sample for segment in segments for sample in segment.samples]
        powers = [float(sample.power_percent) for sample in samples if sample.power_percent is not None]
        scores = [float(sample.score_percent) for sample in samples if sample.score_percent is not None]
        return TelemetryEvidence(
            path=str(path),
            segment_count=len(segments),
            sample_count=len(samples),
            power_min=min(powers) if powers else None,
            power_max=max(powers) if powers else None,
            score_min=min(scores) if scores else None,
            score_max=max(scores) if scores else None,
        )

    @staticmethod
    def _interpret(profile: BinaryProfile, family: str) -> tuple[str, str]:
        top = profile.numeric_candidates[0] if profile.numeric_candidates else None
        if top is None:
            return "No stable numeric array candidate detected", "Unknown"
        if family == "SpectrumMsg" and top.dtype in {"<f4", ">f4"} and top.nonnegative_ratio > 0.9:
            return "Spectrum-like floating-point array candidate; header and scaling remain unconfirmed", "Estimated"
        if family == "Acquisition" and top.score >= 65:
            return "High-quality numeric payload candidate; may contain waveform, FFT, or DSP intermediates", "Estimated"
        return "Numeric payload detected, semantic meaning not established", "Unknown"

    @staticmethod
    def _build_conclusions(report: ReverseEngineeringReport) -> list[dict]:
        families: dict[str, list[FileEvidence]] = {}
        for item in report.files:
            families.setdefault(item.family, []).append(item)
        conclusions: list[dict] = []
        if families.get("SpectrumMsg"):
            conclusions.append({
                "status": "Confirmed",
                "finding": "SpectrumMsg files are present in Sonication exports and contain repeatable numeric payload candidates.",
            })
        if families.get("Acquisition"):
            conclusions.append({
                "status": "Confirmed",
                "finding": "Acquisition DMP files are present and must be analyzed independently from SpectrumMsg; they are not assumed to be equivalent.",
            })
        if report.telemetry:
            conclusions.append({
                "status": "Confirmed",
                "finding": "Acquisition_Brain telemetry exposes Power and Score time series usable as an external validation target.",
            })
        conclusions.append({
            "status": "Unknown",
            "finding": "The exact Workstation amplitude scaling, FFT window, baseline subtraction, and channel multiplexing remain unconfirmed until candidate arrays correlate with Score events.",
        })
        conclusions.append({
            "status": "Safety",
            "finding": "No candidate decode is promoted into the Replay display by this commit; reports are diagnostic only.",
        })
        return conclusions

    @staticmethod
    def _write_outputs(report: ReverseEngineeringReport, output_dir: Path) -> None:
        payload = report.to_dict()
        (output_dir / "hydrophone_reverse_engineering_report.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        with (output_dir / "binary_candidates.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "family", "path", "sonication", "main_frequency_hz", "configured_channel",
                "dtype", "offset", "count", "score", "finite_ratio", "nonnegative_ratio",
                "dynamic_ratio", "smoothness", "interpretation", "confidence",
            ])
            for item in report.files:
                candidates = item.profile.get("numeric_candidates", [])
                if not candidates:
                    writer.writerow([item.family, item.path, item.sonication, item.main_frequency_hz, item.configured_channel, "", "", "", "", "", "", "", "", item.interpretation, item.confidence])
                    continue
                for candidate in candidates[:10]:
                    writer.writerow([
                        item.family, item.path, item.sonication, item.main_frequency_hz, item.configured_channel,
                        candidate.get("dtype"), candidate.get("offset"), candidate.get("count"), candidate.get("score"),
                        candidate.get("finite_ratio"), candidate.get("nonnegative_ratio"), candidate.get("dynamic_ratio"),
                        candidate.get("smoothness"), item.interpretation, item.confidence,
                    ])
        with (output_dir / "telemetry_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["path", "segment_count", "sample_count", "power_min", "power_max", "score_min", "score_max"])
            for item in report.telemetry:
                writer.writerow([item.path, item.segment_count, item.sample_count, item.power_min, item.power_max, item.score_min, item.score_max])
        (output_dir / "README.txt").write_text(
            "Hydrophone Reverse Engineering Report\n\n"
            "Confirmed = directly supported by file/log structure.\n"
            "Estimated = plausible numeric interpretation requiring correlation.\n"
            "Unknown = not established.\n\n"
            "Do not use candidate arrays for clinical or service decisions.\n",
            encoding="utf-8",
        )
