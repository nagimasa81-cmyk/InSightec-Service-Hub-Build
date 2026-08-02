from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_quick_spike_real_execution_markers():
    assert "Building FFT" in SOURCE
    assert "Validating k-space spikes" in SOURCE
    assert "analysis_completed" in SOURCE
    assert "Detection Stages Completed" in SOURCE
    assert "_raw_spike_features(magnitude, valid)" in SOURCE


def test_collapsed_series_opens_first_image():
    assert 'if source_type == "series":' in SOURCE
    assert "item.setExpanded(True)" in SOURCE
    assert "self.tree.setCurrentItem(first_leaf)" in SOURCE
    assert "self.show_dicom(int(first_data[1]))" in SOURCE
