from __future__ import annotations

"""Reusable thread-safe LRU caches for image-oriented desktop tools.

Commit0084 adds a value-owning cache beside the existing key-only cache.  The
value cache is intentionally generic so the same implementation can be reused
for decoded images, FFT arrays and thumbnails without introducing Qt objects
into the cache layer.
"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUKeySet(Generic[K]):
    """Thread-safe, bounded set ordered by most-recent use."""

    def __init__(self, capacity: int, on_evict: Optional[Callable[[K], None]] = None):
        self._capacity = max(1, int(capacity))
        self._on_evict = on_evict
        self._keys: OrderedDict[K, None] = OrderedDict()
        self._lock = RLock()

    @property
    def capacity(self) -> int:
        return self._capacity

    def set_capacity(self, capacity: int) -> list[K]:
        with self._lock:
            self._capacity = max(1, int(capacity))
            return self._trim_locked()

    def touch(self, key: K) -> list[K]:
        with self._lock:
            self._keys.pop(key, None)
            self._keys[key] = None
            return self._trim_locked()

    def discard(self, key: K) -> None:
        with self._lock:
            self._keys.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._keys.clear()

    def snapshot(self) -> tuple[K, ...]:
        with self._lock:
            return tuple(self._keys.keys())

    def _trim_locked(self) -> list[K]:
        evicted: list[K] = []
        while len(self._keys) > self._capacity:
            key, _ = self._keys.popitem(last=False)
            evicted.append(key)
            if self._on_evict is not None:
                self._on_evict(key)
        return evicted


class LRUCache(Generic[K, V]):
    """Thread-safe bounded LRU value cache with lightweight hit statistics."""

    def __init__(
        self,
        capacity: int,
        on_evict: Optional[Callable[[K, V], None]] = None,
    ):
        self._capacity = max(1, int(capacity))
        self._on_evict = on_evict
        self._values: OrderedDict[K, V] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            if key not in self._values:
                self._misses += 1
                return default
            value = self._values.pop(key)
            self._values[key] = value
            self._hits += 1
            return value

    def put(self, key: K, value: V) -> list[tuple[K, V]]:
        with self._lock:
            old = self._values.pop(key, None)
            if old is not None and old is not value and self._on_evict is not None:
                self._on_evict(key, old)
            self._values[key] = value
            return self._trim_locked()

    def discard(self, key: K) -> Optional[V]:
        with self._lock:
            return self._values.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            items = list(self._values.items())
            self._values.clear()
        if self._on_evict is not None:
            for key, value in items:
                self._on_evict(key, value)

    def set_capacity(self, capacity: int) -> list[tuple[K, V]]:
        with self._lock:
            self._capacity = max(1, int(capacity))
            return self._trim_locked()

    def snapshot(self) -> tuple[K, ...]:
        with self._lock:
            return tuple(self._values.keys())

    def stats(self) -> "ValueCacheStats":
        with self._lock:
            return ValueCacheStats(
                size=len(self._values),
                capacity=self._capacity,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                keys=tuple(self._values.keys()),
            )

    def _trim_locked(self) -> list[tuple[K, V]]:
        evicted: list[tuple[K, V]] = []
        while len(self._values) > self._capacity:
            key, value = self._values.popitem(last=False)
            evicted.append((key, value))
            self._evictions += 1
            if self._on_evict is not None:
                self._on_evict(key, value)
        return evicted


@dataclass(frozen=True)
class CacheStats:
    size: int
    capacity: int
    keys: tuple[Hashable, ...]


@dataclass(frozen=True)
class ValueCacheStats:
    size: int
    capacity: int
    hits: int
    misses: int
    evictions: int
    keys: tuple[Hashable, ...]

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return float(self.hits / total) if total else 0.0


def cache_stats(cache: LRUKeySet) -> CacheStats:
    keys = cache.snapshot()
    return CacheStats(size=len(keys), capacity=cache.capacity, keys=keys)
