from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    '"GESYS": "GESYS"',
    '"LAIS": "LAIS"',
    '"PSC": "PSC"',
    '"REVIEW": "Review"',
    "PARSER_MAP",
    "LOG_PARSERS",
    "FILE_TYPE_PARSERS",
    "SUPPORTED_TYPES",
    "KNOWN_LOG_TYPES",
]:
    assert token in source, token

entry = source.rfind('if __name__ == "__main__":')
patch = source.index("# Commit0032B:")
assert patch < entry

print("Commit0032B discovery/parser/viewer contract: PASS")
