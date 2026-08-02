from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_result_mode_hides_auto_correct():
    block = SOURCE.split("def _set_auto_result_mode", 1)[1].split("def run_auto_correct_again", 1)[0]
    assert "self.comp_auto_correct_button.setVisible(not completed)" in block
    assert "self.comp_next_step_group.setVisible(True)" in block
    assert "self.comp_next_step_group.setVisible(False)" in block
    assert "self.comp_auto_more_button.setVisible(completed)" in block


def test_direct_review_rebuilds_before_opening():
    block = SOURCE.split("def review_current_edited_mask", 1)[1].split("def review_reconstructed_image", 1)[0]
    assert "self.preview_compensation()" in block
    assert "self.review_reconstructed_image()" in block
    assert "if self.compensation_preview is None:" in block
    assert block.index("self.preview_compensation()") < block.index("self.review_reconstructed_image()")


def test_more_menu_can_rerun_auto_correct():
    assert 'addAction("Run Auto Correct Again")' in SOURCE
    assert "self.comp_run_auto_again_action.triggered.connect(self.run_auto_correct_again)" in SOURCE
