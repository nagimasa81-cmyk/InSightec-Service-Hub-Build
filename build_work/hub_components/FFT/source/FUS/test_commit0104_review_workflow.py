from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_app_syntax():
    ast.parse(APP)

def test_quick_adjust_is_single_calculation():
    assert "def recalculate_quick_adjust_once" in APP
    block = APP.split("def recalculate_quick_adjust_once", 1)[1].split("def restore_auto_compensation_result", 1)[0]
    assert "recalculate_with_mask(" in block
    assert "auto_correct_with_retry(" not in block
    assert "auto_correct_with_retry(" not in block

def test_review_button_and_next_step_actions():
    for text in ["Review Reconstructed Image", "OK — Use This Result", "Quick Adjust", "Paint", "Expert"]:
        assert text in APP
    assert "self.comp_next_step_group.setVisible(True)" in APP

def test_auto_correct_opens_review_for_reliable_result():
    block = APP.split("def auto_correct_compensation", 1)[1].split("def invalidate_compensation_detection", 1)[0]
    assert "self.review_reconstructed_image()" in block

def test_expert_scope_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Expert" in readme and "mask expansion" in readme.lower()
