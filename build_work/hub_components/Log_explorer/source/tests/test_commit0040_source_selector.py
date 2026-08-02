from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

for token in [
    "def _c40_refresh_available_sources",
    '"GESYS": "GESYS"',
    '"PSC": "PSC"',
    'available = ["Merged"] + available',
]:
    assert token in source, token

print("Commit0040 cached source selector: PASS")
