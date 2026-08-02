from __future__ import annotations

from pathlib import Path

import numpy as np

from src.core.models import (
    ImageFrame,
    ReplayFrame,
    SonicationReplay,
    TemperatureFrame,
)
from src.core.spectrum_provider import NullSpectrumProvider


class ReplayBuilder:
    def __init__(self, spectrum_provider=None) -> None:
        self.spectrum_provider = spectrum_provider or NullSpectrumProvider()

    def build(
        self,
        name: str,
        folder: Path,
        magnitude_frames: list[ImageFrame],
        temperature_frames: list[TemperatureFrame],
        act_files: list[Path],
        spectrum_files: list[Path],
    ) -> SonicationReplay:
        spectrum_frames = self.spectrum_provider.load_frames(folder)
        total = max(
            1,
            len(magnitude_frames),
            len(temperature_frames),
            len(spectrum_frames),
        )

        frames: list[ReplayFrame] = []
        for index in range(total):
            position = 0.0 if total == 1 else index / (total - 1)
            frames.append(
                ReplayFrame(
                    index=index,
                    normalized_position=position,
                    magnitude=self._pick(magnitude_frames, position),
                    temperature=self._pick(temperature_frames, position),
                    spectrum=self._pick(spectrum_frames, position),
                )
            )

        return SonicationReplay(
            name=name,
            folder=folder,
            frames=frames,
            act_files=act_files,
            spectrum_files=spectrum_files,
        )

    @staticmethod
    def _pick(items, position):
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        index = int(round(position * (len(items) - 1)))
        return items[max(0, min(index, len(items) - 1))]
