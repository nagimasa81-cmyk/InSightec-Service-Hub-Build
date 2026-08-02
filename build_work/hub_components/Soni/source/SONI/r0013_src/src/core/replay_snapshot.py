from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from src.core.replay_context import ReplaySelection


@dataclass(frozen=True, slots=True)
class ReplayFrameSnapshot:
    """Immutable data package used to render one replay cursor position.

    All mapped indices are resolved once here. Views consume these values and
    must not independently remap the current replay cursor.
    """

    selection: ReplaySelection
    frame_data: Any
    elapsed_seconds: float
    magnitude_index: int | None
    temperature_index: int | None
    spectrum_index: int | None
    spectrum_indices: tuple[tuple[str, int], ...]
    spectrum_count: int
    source_generation: int

    def spectrum_index_for(self, channel: str) -> int | None:
        return dict(self.spectrum_indices).get(channel)


class ReplaySnapshotProvider:
    """Build and cache atomic frame snapshots for the active sonication."""

    def __init__(
        self,
        frame_loader: Callable[[Any, int], Any],
        seconds_mapper: Callable[[int, int], float],
        index_mapper: Callable[[int, int, int], int],
    ) -> None:
        self._frame_loader = frame_loader
        self._seconds_mapper = seconds_mapper
        self._index_mapper = index_mapper
        self._sonication: Any | None = None
        self._sonication_index = -1
        self._spectrum_counts: dict[str, int] = {}
        self._spectrum_count = 0
        self._generation = 0
        self._cache: dict[tuple[int, int, int, int], ReplayFrameSnapshot] = {}

    @property
    def generation(self) -> int:
        return self._generation

    def bind_sonication(
        self,
        sonication_index: int,
        sonication: Any,
        spectrum_count: int | Mapping[str, int],
    ) -> int:
        """Atomically replace all frame sources and invalidate old snapshots."""
        self._sonication_index = int(sonication_index)
        self._sonication = sonication
        if isinstance(spectrum_count, Mapping):
            self._spectrum_counts = {
                str(name): max(0, int(count)) for name, count in spectrum_count.items()
            }
            self._spectrum_count = max(self._spectrum_counts.values(), default=0)
        else:
            self._spectrum_count = max(0, int(spectrum_count))
            self._spectrum_counts = {"CH0": self._spectrum_count} if self._spectrum_count else {}
        self._generation += 1
        self._cache.clear()
        return self._generation

    def clear(self) -> None:
        self._sonication = None
        self._sonication_index = -1
        self._spectrum_counts.clear()
        self._spectrum_count = 0
        self._generation += 1
        self._cache.clear()

    def resolve(self, selection: ReplaySelection) -> ReplayFrameSnapshot | None:
        sonication = self._sonication
        if sonication is None or selection.sonication_index != self._sonication_index:
            return None
        frame_count = max(0, int(selection.frame_count))
        if frame_count <= 0:
            return None
        frame_index = min(max(0, int(selection.frame_index)), frame_count - 1)
        key = (self._generation, self._sonication_index, frame_index, selection.channel_index)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        frame_data = self._frame_loader(sonication, frame_index)
        elapsed = float(self._seconds_mapper(frame_index, frame_count))
        mapped = tuple(
            (name, self._index_mapper(frame_index, frame_count, count))
            for name, count in sorted(self._spectrum_counts.items())
            if count > 0
        )
        spectrum_index = mapped[0][1] if mapped else None

        snapshot = ReplayFrameSnapshot(
            selection=selection,
            frame_data=frame_data,
            elapsed_seconds=elapsed,
            magnitude_index=getattr(frame_data, "magnitude_index", None),
            temperature_index=getattr(frame_data, "temperature_index", None),
            spectrum_index=spectrum_index,
            spectrum_indices=mapped,
            spectrum_count=self._spectrum_count,
            source_generation=self._generation,
        )
        self._cache[key] = snapshot
        return snapshot
