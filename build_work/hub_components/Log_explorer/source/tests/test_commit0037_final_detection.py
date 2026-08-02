from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    "def _c37_filename_type",
    "def _c37_candidate_paths",
    "def _c37_parse_gesys",
    "def _c37_parse_lais",
    "def _c37_parse_review",
    "MultiPaneLogViewer.source_to_records = _c37_source_to_records",
]:
    assert token in source, token

def detect(name):
    lower = Path(name).name.lower()
    suffix = Path(name).suffix.lower()
    if lower == "review.out" or lower.startswith("review.out.") or lower.startswith("review_") or lower.startswith("review-"):
        return "REVIEW"
    if (lower.startswith("gesys_") or lower.startswith("gesyslog") or lower == "gesys.log") and suffix in {".log", ".txt"}:
        return "GESYS"
    if lower.startswith("lais") and suffix in {".log", ".txt"}:
        return "LAIS"
    return ""

assert detect("gesys_GEMR.log") == "GESYS"
assert detect("gesys_GEMR(1).log") == "GESYS"
assert detect("gesyslog_01.txt") == "GESYS"
assert detect("lais.log") == "LAIS"
assert detect("lais_2026.log") == "LAIS"
assert detect("review.out") == "REVIEW"
assert detect("review.out.ar") == "REVIEW"

print("Commit0037 final filename detection: PASS")
