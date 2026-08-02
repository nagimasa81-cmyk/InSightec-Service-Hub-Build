from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_quick_adjust_keeps_original_raw_baseline():
    assert "if self.compensation_original_kspace is None:" in APP
    assert "self.compensation_original_kspace = source.copy()" in APP
    assert "np.asarray(self.compensation_original_kspace).copy()" in APP


def test_quick_adjust_does_not_replace_auto_restore_point():
    assert "store_as_auto_result=False" in APP
    assert "if store_as_auto_result:" in APP
    assert "self.comp_auto_original_mask" in APP


def test_auto_correct_stores_restore_point():
    assert "store_as_auto_result=True" in APP


def test_paint_and_expert_share_manual_handoff():
    assert "def _enter_manual_edit_from_auto_result" in APP
    assert "def open_paint_after_auto_correct" in APP
    assert "def open_expert_after_auto_correct" in APP
    assert APP.count("self._enter_manual_edit_from_auto_result(") >= 2
    assert "panel.manual_mask = existing_mask" in APP
    assert "self.current_kspace = source.copy()" in APP
