from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")

def test_shared_manual_handoff_exists():
    assert "def _enter_manual_edit_from_auto_result" in APP
    assert "existing_mask = candidate.copy()" in APP
    assert "self.current_kspace = source.copy()" in APP
    assert "panel.manual_mask = existing_mask" in APP

def test_paint_and_expert_use_handoff():
    assert "def open_paint_after_auto_correct" in APP
    assert "self._enter_manual_edit_from_auto_result(1)" in APP
    assert "def open_expert_after_auto_correct" in APP
    assert "self._enter_manual_edit_from_auto_result(2)" in APP

def test_expert_buttons_are_routed():
    assert "self.comp_expert_toggle_button.clicked.connect(self.open_expert_after_auto_correct)" in APP
    assert "self.comp_result_expert_button.clicked.connect(self.open_expert_after_auto_correct)" in APP
