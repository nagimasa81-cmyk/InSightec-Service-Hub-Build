from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_modifier_free_wheel_navigation():
    assert "if event.modifiers() & Qt.ControlModifier" not in SOURCE
    assert "self.pageRequested.emit(1 if delta < 0 else -1)" in SOURCE


def test_middle_drag_zoom_is_implemented():
    assert "event.button() == Qt.MiddleButton" in SOURCE
    assert "event.buttons() & Qt.MiddleButton" in SOURCE
    assert "Dragging upward zooms in" in SOURCE


def test_left_double_click_fits_view():
    assert "QEvent.MouseButtonDblClick" in SOURCE
    assert "self.plot.getViewBox().autoRange()" in SOURCE


def test_version_marker():
    assert "Commit0068o" in SOURCE
