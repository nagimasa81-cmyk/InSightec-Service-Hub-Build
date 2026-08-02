from pathlib import Path
ROOT=Path(__file__).resolve().parent
APP=(ROOT/'app.py').read_text(encoding='utf-8')
AUTO=(ROOT/'core'/'auto_correct.py').read_text(encoding='utf-8')

def test_version():
    assert '"commit": "0112"' in (ROOT/'version.json').read_text()
    assert '5.41.0 RC1 Commit0112' in APP

def test_single_difference_window():
    assert 'preview_compensation(open_comparison=False)' in APP
    assert 'existing.close()' in APP
    assert 'WA_DeleteOnClose' in APP

def test_expert_spin_arrows_manual_override():
    assert 'value_control.setEnabled(True)' in APP
    assert 'a.setChecked(False)' in APP

def test_expert_auto_mask_and_candidate_viewer():
    assert 'Run Auto Mask Once' in APP
    assert 'Merge With Current Mask' in APP
    assert 'Candidate Viewer' in APP
    assert 'def run_expert_auto_mask_once' in APP

def test_auto_correct_scoring_improvements():
    assert 'robust_sigma' in AUTO
    assert 'adaptive_offset' in AUTO
    assert 'candidate_score' in AUTO
    assert 'edge_preservation' in AUTO
    assert 'mask_coverage' in AUTO

def test_paint_mask_tools():
    for token in ('Undo Mask','Redo Mask','Symmetry Paint','Expand Mask','Shrink Mask','Fill Largest Region','Delete Smallest Region'):
        assert token in APP
