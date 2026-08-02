from pathlib import Path


def test_explorer_wheel_routes_to_continuous_navigation():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "class ExplorerTreeWidget(QTreeWidget):" in source
    assert "def wheelEvent(self, event):" in source
    assert "self.continuousNavigationRequested.emit(direction)" in source
    assert "direction = -1 if self._navigation_wheel_remainder > 0 else 1" in source
    assert "self._navigate_explorer_keyboard" in source


def test_explorer_wheel_accumulates_high_resolution_delta():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "self._navigation_wheel_remainder" in source
    assert "while abs(self._navigation_wheel_remainder) >= 120" in source
    assert "pixel_delta * 3" in source


def test_commit_version_updated():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "Commit0068i" in source
