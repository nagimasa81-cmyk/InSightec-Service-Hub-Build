from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for source_type in ("GESYS", "LAIS", "PSC", "Review"):
    assert f'"{source_type}"' in source

for token in [
    "read_text(encoding=encoding)",
    "if not line.strip()",
    "_c32b_make_record",
    "_c32b_timestamp_from_text",
    "return records",
]:
    assert token in source, token

# The recovery parser must retain non-empty lines rather than rejecting rows
# merely because a timestamp was not found.
parse_start = source.index("def _c32b_parse_text_log")
parse_end = source.index("def _c32b_parser_dispatch", parse_start)
parse_source = source[parse_start:parse_end]
assert "if timestamp is None" not in parse_source
assert "records.append(" in parse_source

print("Commit0032B loss-tolerant parser flow: PASS")
