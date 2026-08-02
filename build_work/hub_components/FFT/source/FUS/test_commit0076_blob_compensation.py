import ast
from pathlib import Path
import numpy as np

APP=Path(__file__).with_name('app.py')
TEXT=APP.read_text(encoding='utf-8')
TREE=ast.parse(TEXT)

def test_no_full_line_proposals():
    fn=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name=='_suppress_image_spikes')
    src=ast.get_source_segment(TEXT,fn)
    assert 'add_axis_groups' not in src
    assert 'complete row/column and oblique line proposals are intentionally' in src

def test_blob_detector_present():
    assert '_derived_kspace_cluster_candidates' in TEXT
    assert '_box_blur_2d' in TEXT
    assert 'compactness' in TEXT and 'elongation' in TEXT

def test_roi_is_selective_and_confidence_weighted():
    fn=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name=='_interpolate_rectangle')
    src=ast.get_source_segment(TEXT,fn)
    assert 'local_res' in src
    assert 'confidence=np.clip' in src
    assert 'adaptive_alpha' in src
    assert 'outlier &=' in src

def test_version():
    assert any(tag in Path(APP.with_name('version.json')).read_text(encoding='utf-8') for tag in ('Commit0076','Commit0077','Commit0078','Commit0079','Commit0080'))
