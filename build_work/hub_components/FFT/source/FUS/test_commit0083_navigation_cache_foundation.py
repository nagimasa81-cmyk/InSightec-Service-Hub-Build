from pathlib import Path

from core.cache_engine import LRUKeySet
from core.dicom_provider import DicomNavigationProvider


def test_lru_evicts_oldest_and_refreshes_hits():
    evicted = []
    cache = LRUKeySet(2, evicted.append)
    cache.touch(1)
    cache.touch(2)
    cache.touch(1)
    cache.touch(3)
    assert cache.snapshot() == (1, 3)
    assert evicted == [2]


def test_navigation_crosses_series_in_display_order():
    current = {"value": 11}
    provider = DicomNavigationProvider(
        groups_factory=lambda: [("A", [10, 11]), ("B", [20, 21])],
        current_index=lambda: current["value"],
    )
    result = provider.next()
    assert result is not None
    assert result.current_item == 20
    assert result.series_changed is True
    assert result.location.index_in_group == 0


def test_commit0083_uses_header_first_loading_and_shared_cache():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "stop_before_pixels=True" in source
    assert "LRUKeySet" in source
    assert "_touch_dicom_cache(index)" in source
    assert "Commit0083" in source
