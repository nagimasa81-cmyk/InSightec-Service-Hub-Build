from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from src.core.spectrum_decoder import SharedSpectrumDecoder
from src.services.hydrophone_calibration_service import HydrophoneCalibration


@dataclass(slots=True)
class SpectrumFrame:
    index: int
    frequency: list[float] = field(default_factory=list)
    amplitude: list[float] = field(default_factory=list)
    timestamp_seconds: float | None = None
    confidence: float = 0.0
    source: str = "unavailable"
    main_peak_hz: float | None = None
    decoder_offset: int | None = None
    channel: int | None = None
    source_kind: str = "Sonication"


class SpectrumProvider(Protocol):
    provider_name: str

    def supports(self, files: list[Path]) -> bool: ...
    def load(self, files: list[Path], source_kind: str = "Sonication") -> list[SpectrumFrame]: ...


class NullSpectrumProvider:
    provider_name = "Not connected"

    def supports(self, files: list[Path]) -> bool:
        return False

    def load(self, files: list[Path], source_kind: str = "Sonication") -> list[SpectrumFrame]:
        return []


class SpectrumMsgAnalyzerAdapter:
    provider_name = "SpectrumMsg Analyzer Shared Decoder"

    def __init__(self, main_frequency_hz: float | None = None, calibration: HydrophoneCalibration | None = None) -> None:
        self.main_frequency_hz = main_frequency_hz
        self.calibration = calibration
        self.decoder = SharedSpectrumDecoder()
        self._cache: dict[tuple[tuple[str, ...], float | None], list[SpectrumFrame]] = {}

    def _calibrated_amplitude(self, frequency_hz, amplitude, channel: int):
        if self.calibration is None:
            return np.asarray(amplitude, dtype=float)
        return self.calibration.apply(
            np.asarray(frequency_hz, dtype=float),
            np.asarray(amplitude, dtype=float),
            channel,
        )

    def supports(self, files: list[Path]) -> bool:
        return self.main_frequency_hz is not None and any("spectrummsg" in path.name.lower() for path in files)

    def load(self, files: list[Path], source_kind: str = "Sonication") -> list[SpectrumFrame]:
        key = (tuple(str(path) for path in files) + (source_kind,), self.main_frequency_hz)
        if key in self._cache:
            return self._cache[key]
        if not self.supports(files):
            self._cache[key] = []
            return []

        frames: list[SpectrumFrame] = []
        frame_index = 0
        for path in files:
            for decoded in self.decoder.decode_frames(path, float(self.main_frequency_hz)):
                channel = frame_index % 8
                calibrated = self._calibrated_amplitude(decoded.frequency_hz, decoded.amplitude, channel)
                frames.append(SpectrumFrame(
                    index=frame_index,
                    frequency=[float(value) for value in decoded.frequency_hz],
                    amplitude=[float(value) for value in calibrated],
                    confidence=decoded.confidence,
                    source=str(path),
                    main_peak_hz=decoded.main_peak_hz,
                    decoder_offset=decoded.offset,
                    channel=channel,
                    source_kind=source_kind,
                ))
                frame_index += 1
        self._cache[key] = frames
        return frames
