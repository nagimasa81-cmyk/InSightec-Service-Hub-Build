from __future__ import annotations

"""Folder-aware navigation provider for RAW and Explorer sources."""

from typing import Any, Callable, Optional, Sequence

from .navigation_provider import NavigationLocation, NavigationProvider, NavigationResult


class ExplorerNavigationProvider(NavigationProvider[Any]):
    """Navigate selectable leaves while retaining RAW folder boundaries.

    Tree parents define folders/groups.  The last item in one folder advances
    to the first item in the next folder, and the first item moves backward to
    the last item in the previous folder.
    """

    def __init__(
        self,
        items_factory: Callable[[], Sequence[Any]],
        current_item: Callable[[], Any],
    ) -> None:
        self._items_factory = items_factory
        self._current_item = current_item

    @staticmethod
    def _parent(item: Any) -> Any:
        return item.parent() if item is not None and hasattr(item, "parent") else None

    def _snapshot(self) -> tuple[list[list[Any]], list[Any]]:
        items = [item for item in self._items_factory() if item is not None]
        groups: list[list[Any]] = []
        group_parents: list[Any] = []
        for item in items:
            parent = self._parent(item)
            try:
                group_index = group_parents.index(parent)
            except ValueError:
                group_parents.append(parent)
                groups.append([])
                group_index = len(groups) - 1
            groups[group_index].append(item)
        return groups, items

    @staticmethod
    def _location(item: Any, groups: list[list[Any]], items: list[Any]) -> Optional[NavigationLocation[Any]]:
        if item not in items:
            return None
        for group_index, group in enumerate(groups):
            if item in group:
                return NavigationLocation(
                    item=item,
                    index=items.index(item),
                    count=len(items),
                    group_index=group_index,
                    index_in_group=group.index(item),
                    group_count=len(groups),
                    group_size=len(group),
                )
        return None

    def current(self) -> Optional[NavigationLocation[Any]]:
        groups, items = self._snapshot()
        if not items:
            return None
        current = self._current_item()
        if current not in items:
            current = items[0]
        return self._location(current, groups, items)

    def move(self, delta: int) -> Optional[NavigationResult[Any]]:
        current = self.current()
        if current is None:
            return None
        groups, items = self._snapshot()
        if int(delta) == 0:
            return NavigationResult(False, current)
        step = -1 if int(delta) < 0 else 1
        target_index = max(0, min(current.index + step, len(items) - 1))
        target = self._location(items[target_index], groups, items)
        if target is None:
            return None
        return NavigationResult(target.group_index != current.group_index, target)

    def jump(self, index: int) -> Optional[NavigationResult[Any]]:
        current = self.current()
        groups, items = self._snapshot()
        if not items:
            return None
        target_index = max(0, min(int(index), len(items) - 1))
        target = self._location(items[target_index], groups, items)
        if target is None:
            return None
        return NavigationResult(
            bool(current and target.group_index != current.group_index),
            target,
        )
