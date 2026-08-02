from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text(encoding="utf-8")
DOC = ROOT / "docs" / "Spike_Detection_Review_Deck.md"


def test_commit0073_version_marker_present():
    assert "Commit0073" in APP
    assert "Spike Review Deck + Frame Lock" in APP


def test_image_selection_does_not_queue_delayed_stabilizer():
    show_start = APP.index("def show_dicom")
    show_end = APP.index("def show_dicom_header_popup", show_start)
    show_block = APP[show_start:show_end]
    assert "QTimer.singleShot(0, self._stabilize_layout)" not in show_block
    assert "_render_current_image_atomically()" in show_block


def test_pyqtgraph_autorange_not_used_for_viewer_fit():
    # Only comments/docstrings may mention autoRange; executable viewer calls
    # should use fit_to_image() so the frame does not rebound during navigation.
    executable_mentions = [
        line for line in APP.splitlines()
        if "autoRange(" in line and not line.strip().startswith(('#', '"""'))
    ]
    assert executable_mentions == []


def test_frame_lock_guard_blocks_responsive_relayout():
    assert "_frame_lock_active" in APP
    assert "if getattr(self, \"_frame_lock_active\", False):" in APP


def test_review_deck_document_exists():
    assert DOC.exists()
    text = DOC.read_text(encoding="utf-8")
    assert "Candidate-only inverse FFT" in text
    assert "Original image validation" in text
