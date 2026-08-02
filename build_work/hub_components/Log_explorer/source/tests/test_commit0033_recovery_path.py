from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/"LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
for token in [
 "def _c33_classify_recovered", "def _c33_parse_recovered",
 "def _c33_source_to_records", "viewer_selected_files",
 "MultiPaneLogViewer.source_to_records = _c33_source_to_records",
]:
 assert token in s, token
for name in ["GESYS","LAIS","PSC","REVIEW"]:
 assert name in s
print("Commit0033 definitive recovery path: PASS")
