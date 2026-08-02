from pathlib import Path
root = Path(__file__).resolve().parents[1]
viewer = (root / "foundation" / "viewer.py").read_text(encoding="utf-8")
inv = (root / "foundation" / "investigation.py").read_text(encoding="utf-8")
a = viewer.index("    def set_mode(enabled: bool)")
b = viewer.index("    button.toggled.connect(set_mode)", a)
mode = viewer[a:b]
assert "investigation.load_template()" not in mode
assert "investigation._show_ready_state()" in mode
assert "self.max_visible_rows_per_source = 5000" in inv
assert "Rows/source:" in inv
assert "progress.setRange(0, 1000)" in inv
print("Commit0029 manual start: PASS")
