from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

for token in [
    "def _c40_cache_key",
    "def _c40_cached_records",
    "def _c40_source_to_records",
    "zip_import_records_by_type",
    "cached = _c40_cached_records",
    "MultiPaneLogViewer.source_to_records = _c40_source_to_records",
]:
    assert token in source, token

start = source.index("def _c40_source_to_records")
end = source.index(
    "MultiPaneLogViewer.source_to_records = _c40_source_to_records",
    start,
)

segment = source[start:end]
assert segment.index("cached = _c40_cached_records") < segment.index(
    "return _c40_previous_source_to_records"
)

print("Commit0040 ZIP cache priority: PASS")
