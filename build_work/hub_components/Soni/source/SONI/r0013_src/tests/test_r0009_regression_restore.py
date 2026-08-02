from pathlib import Path

MAIN = Path(__file__).parents[1] / "src" / "ui" / "main_window.py"
TEXT = MAIN.read_text(encoding="utf-8")


def test_initial_sonication_uses_direct_set_frame():
    assert "self.set_frame(self.frame_index, display_mode=initial_mode)" in TEXT


def test_set_frame_decodes_and_renders_synchronously():
    block = TEXT[TEXT.index("    def set_frame("):TEXT.index("    def _update_replay_spectrum", TEXT.index("    def set_frame("))]
    assert "data = self.replay.frame(self.current, target)" in block
    assert "self.overlay.set_overlay(" in block
    assert "self._update_replay_spectrum(snapshot)" in block


def test_navigation_uses_visible_frame_index_not_context_gate():
    assert "self.set_frame(self.frame_index - 1)" in TEXT
    assert "current = self.frame_index" in TEXT
    assert "self.set_frame(self.frame_index + delta)" in TEXT


def test_planning_navigation_returns_to_live_replay():
    assert "def _activate_replay_mode_for_navigation" in TEXT
    assert 'self._main_image_mode = "thermal" if self.current and self.current.temperature_frames else "anatomy"' in TEXT
