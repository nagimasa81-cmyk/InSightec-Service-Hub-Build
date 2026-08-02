from pathlib import Path


def test_commit0119_guide_markers():
    text = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "def show_normal_guide" in text
    assert "Raw Data Compensation is offered only at the end" in text
    assert "def show_guide_library" in text
    assert "force_normal_next_start" in text
    assert "force_raw_after_normal_next_start" in text
    assert "Show the normal usage guide at the next startup" in text
    assert "Offer the Raw Data Compensation guide after the normal guide" in text
    assert text.count("def closeEvent(self, event):") == 1
