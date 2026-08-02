from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

for token in [
    "detected files:",
    "parsed files:",
    "failed files:",
    "parser returned 0 rows",
    "no matching filename found",
]:
    assert token in source, token

print("Commit0037 extraction diagnostics: PASS")
