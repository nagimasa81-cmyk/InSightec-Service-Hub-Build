from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    "Filter contains...",
    "Filter exact...",
    "Clear column filter",
    "_c30_apply_header_filter",
    "_c30_clear_header_filter",
]:
    assert token in source, token

print("Commit0032C existing header filters retained: PASS")
