from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')


def _block():
    return APP.split('def recalculate_quick_adjust_once', 1)[1].split('def restore_auto_compensation_result', 1)[0]


def test_quick_adjust_uses_current_mask_when_present():
    block = _block()
    assert 'if has_mask:' in block
    assert 'recalculate_with_mask(' in block


def test_quick_adjust_runs_one_detection_when_mask_empty():
    block = _block()
    assert 'else:' in block
    assert 'result = run_auto_correct(' in block
    assert 'auto_correct_with_retry(' not in block


def test_no_candidate_keeps_quick_adjust_available():
    block = _block()
    assert 'No reliable artifact mask was detected with the current settings.' in block
    assert 'Change the sliders and try again' in block
    assert 'The current mask is empty' not in block


def test_button_and_version_updated():
    assert 'QPushButton("Apply Quick Adjust")' in APP
    assert '5.40.0 RC1 Commit0111' in APP
