from __future__ import annotations

"""DICOM navigation provider with study-wide, series-aware ordering."""

from typing import Any, Callable, Optional, Sequence

from .navigation_provider import NavigationLocation, NavigationProvider, NavigationResult


class DicomNavigationProvider(NavigationProvider[int]):
    """Navigate every non-empty series in one Study.

    ``groups_factory`` returns the Study series list in display order as
    ``[(series_key, [entry_index, ...]), ...]``.  Moving beyond a series end
    selects the first image of the next series; moving before a series start
    selects the last image of the previous series.
    """

    def __init__(
        self,
        groups_factory: Callable[[], Sequence[tuple[Any, Sequence[int]]]],
        current_index: Callable[[], int],
    ) -> None:
        self._groups_factory = groups_factory
        self._current_index = current_index

    def _snapshot(self) -> tuple[list[tuple[Any, list[int]]], list[int]]:
        study_series = [
            (series_key, list(indices))
            for series_key, indices in self._groups_factory()
            if indices
        ]
        flattened = [item for _series_key, group in study_series for item in group]
        return study_series, flattened

    @staticmethod
    def _index_maps(
        study_series: list[tuple[Any, list[int]]],
        flattened: list[int],
    ) -> tuple[dict[int, int], dict[int, tuple[int, int]]]:
        """Build O(1) lookup maps for repeated navigation operations."""
        flat_positions = {item: pos for pos, item in enumerate(flattened)}
        group_positions: dict[int, tuple[int, int]] = {}
        for group_index, (_series_key, group) in enumerate(study_series):
            for index_in_group, item in enumerate(group):
                group_positions[item] = (group_index, index_in_group)
        return flat_positions, group_positions

    @staticmethod
    def _location(
        target: int,
        study_series: list[tuple[Any, list[int]]],
        flattened: list[int],
    ) -> Optional[NavigationLocation[int]]:
        flat_positions, group_positions = DicomNavigationProvider._index_maps(
            study_series, flattened
        )
        flat_index = flat_positions.get(target)
        group_position = group_positions.get(target)
        if flat_index is None or group_position is None:
            return None
        group_index, index_in_group = group_position
        group = study_series[group_index][1]
        return NavigationLocation(
            item=target,
            index=flat_index,
            count=len(flattened),
            group_index=group_index,
            index_in_group=index_in_group,
            group_count=len(study_series),
            group_size=len(group),
        )

    def current(self) -> Optional[NavigationLocation[int]]:
        study_series, flattened = self._snapshot()
        if not flattened:
            return None
        current = int(self._current_index())
        if current not in flattened:
            current = flattened[0]
        return self._location(current, study_series, flattened)

    def move(self, delta: int) -> Optional[NavigationResult[int]]:
        current = self.current()
        if current is None:
            return None
        study_series, flattened = self._snapshot()
        if int(delta) == 0:
            return NavigationResult(False, current)
        step = -1 if int(delta) < 0 else 1
        target_index = max(0, min(current.index + step, len(flattened) - 1))
        target = self._location(flattened[target_index], study_series, flattened)
        if target is None:
            return None
        return NavigationResult(target.group_index != current.group_index, target)

    def jump(self, index: int) -> Optional[NavigationResult[int]]:
        current = self.current()
        study_series, flattened = self._snapshot()
        if not flattened:
            return None
        target_index = max(0, min(int(index), len(flattened) - 1))
        target = self._location(flattened[target_index], study_series, flattened)
        if target is None:
            return None
        return NavigationResult(
            bool(current and target.group_index != current.group_index),
            target,
        )
