from pathlib import Path

SOURCE = Path(__file__).with_name('app.py').read_text(encoding='utf-8')


def test_image_wheel_uses_continuous_navigation():
    assert 'self.primary_panel.pageRequested.connect(self.change_slice_continuous)' in SOURCE
    assert 'self.secondary_panel.pageRequested.connect(self.change_slice_continuous)' in SOURCE
    assert 'self.primary_panel.pageRequested.connect(self.change_slice)' not in SOURCE
    assert 'self.secondary_panel.pageRequested.connect(self.change_slice)' not in SOURCE


def test_workspace_curtains_exist_and_start_open():
    assert 'self.profile_accordion = AccordionSection(' in SOURCE
    assert '"Crosshair Profile Charts", lower, True' in SOURCE
    assert 'self.right_tools_accordion = AccordionSection(' in SOURCE
    assert '"Right Tool Menu", right_scroll, True' in SOURCE


def test_commit_version_is_visible():
    assert 'Commit0068j' in SOURCE
