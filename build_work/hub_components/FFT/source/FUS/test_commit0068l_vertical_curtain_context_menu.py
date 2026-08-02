from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_right_curtain_uses_vertical_collapsed_header():
    assert 'vertical_when_collapsed=True' in APP
    assert 'header_w = 32' in APP
    assert 'painter.rotate(90)' in APP


def test_viewer_context_menu_has_standard_commands():
    for command in (
        'Previous Image', 'Next Image', 'Fit Image to View',
        'Actual Pixels (1:1)', 'Zoom In', 'Zoom Out',
        'Auto', 'Wide', 'Soft Tissue', 'High Contrast', 'Narrow',
        'Copy Displayed Image', 'Save Displayed Image As...',
        'DICOM Header', 'Orientation', 'Show Crosshair',
    ):
        assert command in APP


def test_right_click_distinguishes_click_from_window_level_drag():
    assert 'self._wl_dragged = False' in APP
    assert 'show_menu = not self._wl_dragged' in APP
    assert 'self._show_mouse_action_menu(global_pos)' in APP
