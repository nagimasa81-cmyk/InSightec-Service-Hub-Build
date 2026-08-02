from __future__ import annotations

"""Provider abstractions used by MR Image Explorer navigation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Iterator, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class NavigationLocation(Generic[T]):
    """A resolved navigation target and its position in the full study/order."""

    item: T
    index: int
    count: int
    group_index: int = 0
    index_in_group: int = 0
    group_count: int = 1
    group_size: int = 1

    @property
    def has_previous(self) -> bool:
        return self.index > 0

    @property
    def has_next(self) -> bool:
        return self.index + 1 < self.count


@dataclass(frozen=True)
class NavigationResult(Generic[T]):
    """Result of one navigation action.

    ``series_changed`` is also used for RAW folder transitions.  The class is
    iterable, so callers may use ``series_changed, current_item = result``.
    ``location`` retains all positional metadata required by the toolbar.
    """

    series_changed: bool
    location: NavigationLocation[T]

    @property
    def current_item(self) -> T:
        return self.location.item

    def __iter__(self) -> Iterator[object]:
        yield self.series_changed
        yield self.current_item


class NavigationProvider(ABC, Generic[T]):
    """Resolve current, previous, next, and arbitrary navigation locations."""

    @abstractmethod
    def current(self) -> Optional[NavigationLocation[T]]:
        raise NotImplementedError

    @abstractmethod
    def move(self, delta: int) -> Optional[NavigationResult[T]]:
        raise NotImplementedError

    @abstractmethod
    def jump(self, index: int) -> Optional[NavigationResult[T]]:
        raise NotImplementedError

    def previous(self) -> Optional[NavigationResult[T]]:
        return self.move(-1)

    def next(self) -> Optional[NavigationResult[T]]:
        return self.move(1)
