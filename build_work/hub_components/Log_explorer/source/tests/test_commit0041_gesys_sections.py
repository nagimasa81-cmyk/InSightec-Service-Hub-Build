from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "LogMergeTool_NoExcel_Main.py"
).read_text(encoding="utf-8")

start = source.index("def _c41_gesys_section_records")
end = source.index("def _c41_parse_zip_file", start)
segment = source[start:end]

for token in [
    "parse_gesys_section_datetime",
    "def flush():",
    "section_lines",
    '"lines": visible',
    'source_type="GESYS"',
]:
    assert token in segment, token

assert "records.append(" in segment

print("Commit0041 GESYS section aggregation: PASS")
