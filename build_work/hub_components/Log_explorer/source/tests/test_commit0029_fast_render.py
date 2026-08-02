from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")
a = source.index("    def load_template")
b = source.index("    def _make_pane", a)
segment = source[a:b]
for token in [
    "row_index % 250 == 0",
    "row_index % 500 == 0",
    "table.setVisible(False)",
    "table.setVisible(True)",
    "progress.setRange(0, 1000)",
    "_row_limit_changed",
]:
    assert token in source or token in segment, token
print("Commit0029 fast render: PASS")
