from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_explorer_uses_keyboard_navigation_widget():
    assert "class ExplorerTreeWidget(QTreeWidget):" in SOURCE
    assert "self.tree = ExplorerTreeWidget()" in SOURCE


def test_up_down_route_to_continuous_navigation():
    assert "continuousNavigationRequested = Signal(int)" in SOURCE
    assert "self.continuousNavigationRequested.emit(" in SOURCE
    assert "self.tree.continuousNavigationRequested.connect(" in SOURCE
    assert "moved = self.change_slice_continuous(delta)" in SOURCE


def test_version_updated():
    assert "Commit0068i" in SOURCE
