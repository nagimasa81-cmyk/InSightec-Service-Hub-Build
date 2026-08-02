from pathlib import Path

SOURCE = Path(__file__).with_name('app.py').read_text(encoding='utf-8')

def test_profile_splitter_ignores_transient_programmatic_sizes():
    assert '_programmatic_splitter_change' in SOURCE
    assert 'expanded and len(sizes) == 2 and sizes[1] >= 180' in SOURCE
    assert '_enforce_profile_curtain_geometry' in SOURCE

def test_fft_back_restores_complete_state():
    assert 'self.fft_back_state = {' in SOURCE
    assert '"raw_window_level": self.raw_window_level' in SOURCE
    assert 'self.raw_window_level = state["raw_window_level"]' in SOURCE
    assert 'self.current_kspace = None if state["kspace"] is None' in SOURCE

def test_clicked_panel_controls_its_own_window_level():
    assert 'def _prepare_level_controls_for_panel' in SOURCE
    assert 'self._panel_role(panel) == "fft"' in SOURCE
