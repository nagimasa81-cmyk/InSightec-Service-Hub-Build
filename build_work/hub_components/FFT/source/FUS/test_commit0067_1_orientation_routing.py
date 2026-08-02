from pathlib import Path

APP = Path(__file__).with_name("app.py").read_text(encoding="utf-8")

def test_fft_never_receives_patient_orientation_labels():
    assert 'self.secondary_panel.set_orientation_labels(orientation_values)' not in APP

def test_both_routes_orientation_to_original_only():
    marker = 'if view_mode == "both":'
    block = APP[APP.index(marker):APP.index('elif view_mode in ("fft", "k-space", "kspace"):', APP.index(marker))]
    assert 'self.primary_panel.set_orientation_labels(orientation_values)' in block
    assert 'self.secondary_panel.set_orientation_labels(empty_values)' in block

def test_fft_only_clears_both_panels():
    marker = 'elif view_mode in ("fft", "k-space", "kspace"):'
    block = APP[APP.index(marker):APP.index('else:', APP.index(marker))]
    assert 'self.primary_panel.set_orientation_labels(empty_values)' in block
    assert 'self.secondary_panel.set_orientation_labels(empty_values)' in block

def test_original_only_routes_to_primary_panel():
    marker = '# Original-only DICOM display.'
    block = APP[APP.index(marker):APP.index('self.current_orientation_labels = labels', APP.index(marker))]
    assert 'self.primary_panel.set_orientation_labels(orientation_values)' in block
    assert 'self.secondary_panel.set_orientation_labels(empty_values)' in block
