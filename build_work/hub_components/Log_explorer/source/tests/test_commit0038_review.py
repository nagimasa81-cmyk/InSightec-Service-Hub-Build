from pathlib import Path
s=(Path(__file__).resolve().parents[1]/"LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
for t in ["def _c38_review_text","def _c38_review_lines","def _c38_review_records",
          "def _c38_review_summary","_c37_parse_review = _c38_review_records",
          "MultiPaneLogViewer.source_to_records = _c38_source_to_records"]:
    assert t in s,t
assert 'raw.replace(b"\\x00", b"\\n")' in s
assert '"rows": len(records)' in s
print("Commit0038 Review parser: PASS")
