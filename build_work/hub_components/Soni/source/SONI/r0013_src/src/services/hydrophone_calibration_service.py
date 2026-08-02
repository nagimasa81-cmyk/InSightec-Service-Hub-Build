from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import numpy as np


@dataclass(slots=True)
class HydrophoneCalibration:
    spectrum_factors: tuple[float, ...] = (1.0,) * 8
    spectrum_coef: float = 1.0
    response_frequency_hz: np.ndarray = field(default_factory=lambda: np.array([], dtype=float))
    response_coefficients: np.ndarray = field(default_factory=lambda: np.empty((0, 8), dtype=float))
    calibration_ini: Path | None = None
    response_ini: Path | None = None

    @property
    def available(self) -> bool:
        return self.calibration_ini is not None or self.response_ini is not None

    def coefficients(self, frequency_hz: np.ndarray, channel: int) -> np.ndarray:
        ch = min(max(int(channel), 0), 7)
        base = float(self.spectrum_coef) * float(self.spectrum_factors[ch])
        if self.response_frequency_hz.size and self.response_coefficients.shape[0] == self.response_frequency_hz.size:
            response = np.interp(
                np.asarray(frequency_hz, dtype=float),
                self.response_frequency_hz,
                self.response_coefficients[:, ch],
                left=self.response_coefficients[0, ch],
                right=self.response_coefficients[-1, ch],
            )
            return base * response
        return np.full(np.asarray(frequency_hz).shape, base, dtype=float)

    def apply(self, frequency_hz: np.ndarray, amplitude: np.ndarray, channel: int) -> np.ndarray:
        return np.asarray(amplitude, dtype=float) * self.coefficients(frequency_hz, channel)


class HydrophoneCalibrationService:
    """Read the CPC hydrophone calibration files and expose deterministic factors."""

    @staticmethod
    def _find(workspace: Path, filename: str) -> Path | None:
        target = filename.lower()
        return next((p for p in workspace.rglob("*") if p.is_file() and p.name.lower() == target), None)

    @staticmethod
    def _clean(line: str) -> str:
        return line.split(";", 1)[0].strip()

    def read(self, workspace: Path) -> HydrophoneCalibration:
        result = HydrophoneCalibration()
        calibration_ini = self._find(workspace, "Calibration.ini")
        response_ini = self._find(workspace, "HydrophonesResponseCalibration.ini")
        result.calibration_ini = calibration_ini
        result.response_ini = response_ini

        if calibration_ini is not None:
            text = calibration_ini.read_text(encoding="utf-8", errors="ignore")
            factor_match = re.search(r"(?im)^\s*SpectrumFactor\s*=\s*([^\r\n;]+)", text)
            if factor_match:
                values = [float(v) for v in factor_match.group(1).split()[:8]]
                if len(values) == 8 and all(np.isfinite(values)):
                    result.spectrum_factors = tuple(values)
            coef_match = re.search(r"(?im)^\s*SpectrumCoef\s*=\s*([-+0-9.eE]+)", text)
            if coef_match:
                value = float(coef_match.group(1))
                if np.isfinite(value):
                    result.spectrum_coef = value

        if response_ini is not None:
            frequencies: list[float] = []
            rows: list[list[float]] = []
            for raw_line in response_ini.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = self._clean(raw_line)
                if not re.match(r"(?i)^FREQ\d+\s*=", line):
                    continue
                _, value_text = line.split("=", 1)
                try:
                    values = [float(v) for v in value_text.split()]
                except ValueError:
                    continue
                if len(values) < 9:
                    continue
                freq = values[0]
                # This file stores MHz values (0.000, 0.002, ...).
                freq_hz = freq * 1_000_000.0 if abs(freq) < 100.0 else freq
                frequencies.append(freq_hz)
                rows.append(values[1:9])
            if frequencies:
                order = np.argsort(np.asarray(frequencies, dtype=float))
                result.response_frequency_hz = np.asarray(frequencies, dtype=float)[order]
                result.response_coefficients = np.asarray(rows, dtype=float)[order]
        return result
