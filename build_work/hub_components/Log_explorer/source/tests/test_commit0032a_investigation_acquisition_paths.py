from pathlib import Path

root = Path(__file__).resolve().parents[1]
main = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
investigation = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")

for token in [
    "def get(self, key: object, default=None)",
    "def __getitem__(self, key: object)",
    "def items(self)",
    "def to_dict(self)",
    '"_ts": "timestamp"',
    '"Message": "message"',
]:
    assert token in main, token

assert 'row.get("_ts")' in investigation
assert 'row.get("Message", "")' in investigation
assert 'rows[index].get("timestamp")' in investigation
assert 'row.get("timestamp")' in investigation

print("Commit0032A Investigation/Acquisition compatibility paths: PASS")
