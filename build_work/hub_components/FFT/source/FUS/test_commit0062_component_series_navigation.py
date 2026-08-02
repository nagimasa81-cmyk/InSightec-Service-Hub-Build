from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_profile_controls_removed_from_visible_right_panel():
    assert 'profile_group = QGroupBox("Profile")' not in APP
    assert 'Component selection now lives directly on each image title.' in APP


def test_each_image_panel_has_independent_component_selector():
    assert 'class ClickableComponentLabel(QLabel)' in APP
    assert 'componentRequested = Signal(str)' in APP
    assert 'self.original_display_mode = "Magnitude"' in APP
    assert 'self.fft_display_mode = "Magnitude"' in APP
    assert 'def _set_panel_component(self, panel, component: str):' in APP


def test_titles_expose_component_menu():
    assert 'Original Image — {original_mode} ▼' in APP
    assert 'FFT (k-space) — {fft_mode} ▼' in APP
    for component in ("Magnitude", "Real", "Imaginary", "Phase"):
        assert component in APP


def test_keyboard_navigation_continues_across_series():
    assert 'keyboardPageRequested = Signal(int)' in APP
    assert 'def change_slice_continuous(self, delta):' in APP
    assert 'group_pos + 1 < len(groups)' in APP
    assert 'group_pos - 1 >= 0' in APP


def test_explorer_follows_active_series():
    assert 'def _set_tree_series_expansion_for_index(self, index: int):' in APP
    assert 'item.setExpanded(item is target_series)' in APP
    assert 'self._set_tree_series_expansion_for_index(target)' in APP
