from __future__ import annotations

from pathlib import Path

from src.core.models import SpectrumFrame


class NullSpectrumProvider:
    def load_frames(self, sonication_folder: Path) -> list[SpectrumFrame]:
        return []


class SpectrumMsgAnalyzerAdapter:
    """
    Future integration point.

    SpectrumMsg Analyzer decoder output is connected through this provider interface.
    """

    def __init__(self, decoder=None) -> None:
        self.decoder = decoder

    def load_frames(self, sonication_folder: Path) -> list[SpectrumFrame]:
        if self.decoder is None:
            return []
        return self.decoder.decode_sonication(sonication_folder)
