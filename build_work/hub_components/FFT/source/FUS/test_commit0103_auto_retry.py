from pathlib import Path
import numpy as np
from core.auto_correct import AUTO_RETRY_TRIALS, AutoCorrectResult, _result_rank


def test_retry_presets_are_exact():
    assert [x['removal'] for x in AUTO_RETRY_TRIALS] == [50, 60, 70, 80, 90, 100]
    assert [x['protection'] for x in AUTO_RETRY_TRIALS] == [85, 75, 65, 55, 45, 35]
    assert all(x['detail'] == 75 for x in AUTO_RETRY_TRIALS)


def test_quality_tie_break_prefers_less_change_then_residual_then_detail():
    z=np.zeros((2,2), dtype=complex); m=np.ones((2,2), dtype=bool)
    a=AutoCorrectResult(z,z.real,m,{'overall_quality':70,'outside_image_change':2,'residual_artifact':20,'detail_preservation':90},[],['Spike'])
    b=AutoCorrectResult(z,z.real,m,{'overall_quality':70,'outside_image_change':3,'residual_artifact':5,'detail_preservation':99},[],['Spike'])
    assert _result_rank(a) > _result_rank(b)


def test_ui_contains_retry_progress_and_failure_actions():
    text=Path('app.py').read_text(encoding='utf-8')
    assert 'Trial {trial} / {total}' in text
    assert 'Searching Artifacts...' in text
    assert 'Evaluating Quality...' in text
    assert 'Manual Paint' in text and 'Expert Settings' in text
    assert 'quality_threshold=60.0' in text
