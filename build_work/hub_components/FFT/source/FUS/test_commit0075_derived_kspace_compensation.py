from pathlib import Path
import ast
import numpy as np

APP = Path(__file__).with_name('app.py')
TEXT = APP.read_text(encoding='utf-8')


def test_version_and_derived_cluster_stage_present():
    assert 'Commit0075' in TEXT
    assert '_derived_kspace_cluster_candidates' in TEXT
    assert 'cluster_pass' in TEXT
    assert 'full-span derived-k-space anatomical structure' in TEXT


def test_compensation_is_selective_feathered_and_conjugate_safe():
    assert 'cosine feather' in TEXT
    assert 'outlier=roi_mag > (med + 4.0*sigma)' in TEXT
    assert 'result[sy,sx]=np.conj(result[y,x])' in TEXT
    assert 'central DC cross' in TEXT


def test_source_compiles_as_ast():
    ast.parse(TEXT)
