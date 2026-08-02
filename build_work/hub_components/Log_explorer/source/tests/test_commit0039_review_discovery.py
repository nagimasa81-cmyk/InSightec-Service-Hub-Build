from pathlib import Path
s=(Path(__file__).resolve().parents[1]/"LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
for token in [
    "def _c39_review_summary",
    "def _c39_apply_review_summary",
    "def _c39_patch_discovery_rows",
    '"rows": len(records)',
    '"row_count": len(records)',
    '"count": len(records)',
    "_c37_parse_review = _c38_review_records",
]:
    assert token in s, token
print("Commit0039 Review Discovery unification: PASS")
