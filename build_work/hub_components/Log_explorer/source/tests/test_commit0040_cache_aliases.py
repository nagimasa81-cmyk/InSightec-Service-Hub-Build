from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

for token in [
    '"GESYSLOG": "GESYS"',
    '"GESYS": "GESYS"',
    '"LAIS": "LAIS"',
    '"PSC": "PSC"',
    '"REVIEW": "REVIEW"',
    '"ACQUISITION": "ACQUISITION"',
]:
    assert token in source, token

print("Commit0040 cache source aliases: PASS")
