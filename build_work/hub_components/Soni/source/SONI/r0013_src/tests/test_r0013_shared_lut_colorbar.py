from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "src/ui/main_window.py").read_text(encoding="utf-8")


def test_color_bar_uses_shared_gamma_aware_colour_path():
    assert "def _display_color(self, normalized_level):" in SOURCE
    assert "def _draw_color_bar(self, painter, bar, lo, hi):" in SOURCE
    assert "self._display_color(normalized)" in SOURCE
    assert "color = self._display_color(level)" in SOURCE


def test_backend_fragile_one_pixel_image_stretch_removed():
    assert "QImage(1, 256" not in SOURCE
    assert "painter.drawImage(bar, gradient_image)" not in SOURCE
    assert "painter.drawLine(left, y, right, y)" in SOURCE


def test_release_metadata():
    assert (ROOT / "VERSION").read_text().strip() in {"RC2-R0013", "RC2-R0014"}
    assert any(x in (ROOT / "version.json").read_text() for x in ('"commit": "R0013"', '"commit": "R0014"'))
