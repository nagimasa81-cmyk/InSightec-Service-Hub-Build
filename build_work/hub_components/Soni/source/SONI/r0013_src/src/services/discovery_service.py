from __future__ import annotations

import re
from pathlib import Path

from src.common.constants import MAGNITUDE_PREFIX, TEMPERATURE_PREFIX, DEFAULT_MAIN_FREQUENCY_HZ
from src.domain.models import RawFrame, ReplayPackage, SonicationModel
from src.services.xd_ini_service import XdIniService
from src.services.sonication_frequency_service import SonicationFrequencyService
from src.services.sonication_timing_service import SonicationTimingService
from src.services.planning_data_service import PlanningDataService


SON_RE = re.compile(r"^sonication\s*[_-]?\s*(\d+)$", re.I)
RAW_RE = re.compile(r"^(\d+)-.*-(\d+)\.raw$", re.I)


def natural_key(text):
    return [
        int(x) if x.isdigit() else x.lower()
        for x in re.split(r"(\d+)", text)
    ]


class DiscoveryService:
    def __init__(self) -> None:
        self.xd_ini = XdIniService()
        self.sonication_frequency = SonicationFrequencyService()
        self.sonication_timing = SonicationTimingService()
        self.planning_data = PlanningDataService()

    def discover(self, source: Path, workspace: Path) -> ReplayPackage:
        dirs = []
        for path in workspace.rglob("*"):
            if path.is_dir() and SON_RE.match(path.name):
                dirs.append(path)

        if SON_RE.match(workspace.name):
            dirs.append(workspace)

        if (
            not dirs
            and any(
                path.is_file()
                and (
                    "spectrummsg" in path.name.lower()
                    or path.suffix.lower() == ".raw"
                )
                for path in workspace.iterdir()
            )
        ):
            dirs = [workspace]

        unique = {path.resolve(): path for path in dirs}
        dirs = sorted(
            unique.values(),
            key=lambda path: natural_key(path.name),
        )
        models = [
            self._build(path, index + 1)
            for index, path in enumerate(dirs)
        ]

        timings = self.sonication_timing.read_all(workspace)
        for index, model in enumerate(models):
            if index < len(timings):
                timing = timings[index]
                model.planned_duration_s = timing.planned_duration_s
                model.actual_duration_s = timing.actual_duration_s
                model.planned_power_w = timing.planned_power_w
                model.timing_source = timing.source

        frequency = self.xd_ini.read_main_frequency(workspace)
        fallback_hz = frequency.frequency_hz if frequency.frequency_hz is not None else DEFAULT_MAIN_FREQUENCY_HZ
        for model in models:
            local = self.sonication_frequency.read(model.folder)
            model.main_frequency_hz = local.frequency_hz if local.frequency_hz is not None else fallback_hz
            model.main_frequency_source = local.source if local.source is not None else frequency.source_path
            model.main_frequency_raw_line = local.raw_line if local.raw_line is not None else frequency.raw_line

        cpc_files = []
        for cpc_dir in (p for p in workspace.rglob('*') if p.is_dir() and p.name.lower() == 'cpcfiles'):
            for path in cpc_dir.rglob('*'):
                if not path.is_file():
                    continue
                low = path.name.lower()
                if low.startswith('spectrum_') and (low.endswith('.dmp') or low.endswith('.dmp_fft')):
                    cpc_files.append(path)
        cpc_files = sorted(set(cpc_files), key=lambda path: natural_key(str(path)))

        # CPCFiles remain independent from Sonication SpectrumMsg.
        # They are consumed only by the dedicated 8CH Hydrophone Analyzer popup.

        planning = self.planning_data.discover(workspace)

        return ReplayPackage(
            source=source,
            workspace=workspace,
            sonications=models,
            main_frequency_hz=frequency.frequency_hz if frequency.frequency_hz is not None else DEFAULT_MAIN_FREQUENCY_HZ,
            main_frequency_source=frequency.source_path,
            main_frequency_raw_line=frequency.raw_line,
            main_frequency_confidence=frequency.confidence,
            main_frequency_interpretation=frequency.unit_interpretation if frequency.frequency_hz is not None else "Default 650 kHz",
            cpc_spectrum_files=cpc_files,
            planning_assets=planning.assets,
        )

    def _build(
        self,
        folder: Path,
        fallback: int,
    ) -> SonicationModel:
        match = SON_RE.match(folder.name)
        name = (
            f"Sonication{int(match.group(1))}"
            if match
            else f"Sonication{fallback}"
        )

        model = SonicationModel(
            name=name,
            folder=folder,
        )

        for path in folder.rglob("*"):
            if not path.is_file():
                continue

            low = path.name.lower()
            raw_match = RAW_RE.match(path.name)

            if raw_match:
                frame = RawFrame(
                    path=path,
                    index=int(raw_match.group(2)),
                    prefix=raw_match.group(1),
                )
                if frame.prefix == TEMPERATURE_PREFIX:
                    model.temperature_frames.append(frame)
                elif frame.prefix == MAGNITUDE_PREFIX:
                    model.magnitude_frames.append(frame)
                else:
                    model.other_files.append(path)
            elif (
                "spectrummsg" in low
                and path.suffix.lower() == ".dmp"
            ):
                model.spectrum_files.append(path)
            elif path.suffix.lower() == ".act":
                model.act_files.append(path)
            else:
                model.other_files.append(path)

        model.temperature_frames.sort(key=lambda frame: frame.index)
        model.magnitude_frames.sort(key=lambda frame: frame.index)
        model.spectrum_files.sort(
            key=lambda path: natural_key(path.name)
        )
        model.act_files.sort(
            key=lambda path: natural_key(path.name)
        )
        return model
