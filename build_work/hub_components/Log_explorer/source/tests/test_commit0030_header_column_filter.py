from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
source = (root / "LogMergeTool_NoExcel_Main.py").read_text(encoding="utf-8")
tree = ast.parse(source)

entry = source.rfind('if __name__ == "__main__":')
assert entry > 0
assert source.count('if __name__ == "__main__":') == 1

for token in [
    'APP_VERSION = "2.0.0-rc1-commit0030"',
    "def _c30_parse_column_filter",
    "def _c30_manual_expression_matches",
    "Filter contains...",
    "Filter exact...",
    "Clear column filter",
    "header.customContextMenuRequested.connect",
    "MultiPaneLogViewer.build_ui = _c30_viewer_build_ui",
]:
    position = source.find(token)
    assert 0 <= position < entry, token

print("Commit0030 header column filter integration: PASS")
