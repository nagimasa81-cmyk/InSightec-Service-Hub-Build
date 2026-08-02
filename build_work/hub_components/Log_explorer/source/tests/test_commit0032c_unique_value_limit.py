from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

start = source.index("def _c32c_column_unique_values")
end = source.index("def _c32c_apply_selected_value", start)
segment = source[start:end]

assert "if len(unique) >= limit:" in segment
assert "return []" in segment
assert "limit=11" in segment
assert "display_value.casefold()" in segment
assert 'display_value = "" if raw_value is None else str(raw_value)' in segment

print("Commit0032C 10-value threshold logic: PASS")
