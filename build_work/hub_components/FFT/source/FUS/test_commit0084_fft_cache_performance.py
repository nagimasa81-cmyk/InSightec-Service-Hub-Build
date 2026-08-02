import numpy as np

from core.cache_engine import LRUCache


def test_lru_value_cache_evicts_oldest_and_tracks_hits():
    cache = LRUCache(capacity=2)
    cache.put("a", np.array([1]))
    cache.put("b", np.array([2]))
    assert cache.get("a")[0] == 1
    cache.put("c", np.array([3]))
    assert cache.get("b") is None
    assert cache.get("a")[0] == 1
    stats = cache.stats()
    assert stats.capacity == 2
    assert stats.evictions == 1
    assert stats.hits >= 2
    assert stats.misses >= 1


def test_source_contains_commit0084_fft_cache_path():
    source = open("app.py", encoding="utf-8").read()
    assert "Commit0084" in source
    assert "self.fft_cache" in source
    assert "_fft_for_current_image" in source
    assert "MR_IMAGE_FFT_CACHE" in source
    assert "MR_IMAGE_PERFORMANCE_LOG" in source
