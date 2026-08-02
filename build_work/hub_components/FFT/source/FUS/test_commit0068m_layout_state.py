from pathlib import Path

SOURCE = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def test_profile_state_respected_by_responsive_layout():
    assert 'profile_expanded = self.profile_accordion.button.isChecked()' in SOURCE
    assert 'if profile_expanded:' in SOURCE
    assert 'header_h = self.profile_accordion.button.sizeHint().height() + 8' in SOURCE


def test_right_curtain_state_respected_by_responsive_layout():
    assert 'right_expanded = self.right_tools_accordion.button.isChecked()' in SOURCE
    assert 'if right_expanded:' in SOURCE
    assert 'header_w = 32' in SOURCE


def test_splitter_ratios_are_preserved():
    assert '_user_viewer_content_split_sizes' in SOURCE
    assert '_user_vertical_split_sizes' in SOURCE
    assert '_user_image_split_sizes' in SOURCE
    assert 'viewer_content_split' in SOURCE


def test_display_reset_reapplies_current_curtain_states():
    assert 'self._profile_curtain_toggled(' in SOURCE
    assert 'self.profile_accordion.button.isChecked()' in SOURCE
    assert 'self._right_tools_curtain_toggled(' in SOURCE
    assert 'self.right_tools_accordion.button.isChecked()' in SOURCE
