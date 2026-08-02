from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (
    root / "foundation" / "spectrum_analysis.py"
).read_text(encoding="utf-8")

assert "QRectF(plot).contains(self.crosshair_pos)" in source
assert "plot.contains(self.crosshair_pos)" not in source
assert "self.zoom_rect = QRectF(rect)" in source

print("Commit0034 Spectrum QPointF paint compatibility: PASS")
