from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_expert_review_button_exists():
    assert 'self.comp_expert_review_button = QPushButton("Review Reconstructed Image")' in SOURCE
    assert 'self.comp_expert_review_button.clicked.connect(self.review_current_edited_mask)' in SOURCE


def test_expert_review_rebuilds_current_mask():
    assert 'def review_current_edited_mask(self):' in SOURCE
    assert 'if self.compensation_preview is None:' in SOURCE
    assert 'self.preview_compensation()' in SOURCE


def test_expert_review_does_not_switch_to_paint_tab():
    block = SOURCE.split('def review_current_edited_mask(self):', 1)[1].split('def review_reconstructed_image(self):', 1)[0]
    assert 'setCurrentIndex(1)' not in block
    assert 'open_paint_after_auto_correct' not in block
