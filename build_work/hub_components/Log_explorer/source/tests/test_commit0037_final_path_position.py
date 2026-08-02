from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")

entry = source.rfind('if __name__ == "__main__":')
patch = source.rfind("# Commit0037:")
assignment = source.rfind(
    "MultiPaneLogViewer.source_to_records = _c37_source_to_records"
)

assert 0 <= patch < assignment < entry
assert source.count('if __name__ == "__main__":') == 1

print("Commit0037 final override position: PASS")
