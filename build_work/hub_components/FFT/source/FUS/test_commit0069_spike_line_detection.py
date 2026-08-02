from pathlib import Path
SOURCE = Path('app.py').read_text(encoding='utf-8')

def test_commit_and_line_detector_contract():
    assert 'Commit0069' in SOURCE
    assert 'abnormal_rows' in SOURCE
    assert 'abnormal_cols' in SOURCE
    assert 'row_score' in SOURCE
    assert 'col_score' in SOURCE
    assert 'line_mask' in SOURCE

def test_frequency_marker_contract():
    assert 'InPlanePhaseEncodingDirection' in SOURCE
    assert 'set_frequency_direction' in SOURCE
    assert 'self.frequency_marker' in SOURCE
    assert 'FREQ' not in SOURCE

def test_shared_default_geometry_contract():
    assert 'def _apply_default_image_geometry' in SOURCE
    assert SOURCE.count('_apply_default_image_geometry()') >= 2
