from pathlib import Path

SOURCE = Path(__file__).with_name('app.py').read_text(encoding='utf-8')

def test_review_steps_exist():
    for text in ('STEP 1 Input','STEP 2 FFT','STEP 3 Candidates','STEP 4 IFFT','STEP 5 Correlation','STEP 6 Decision','STEP 7 Compensation'):
        assert text in SOURCE

def test_raw_source_is_explicit():
    assert 'acquired scanner RAW samples are not present' in SOURCE
    assert 'FFT Input (spatial-domain pixels)' in SOURCE

def test_rejected_candidates_are_reviewable():
    assert 'reviewed_regions' in SOURCE
    assert '"decision":"PASS" if is_accepted else "REJECT"' in SOURCE
    assert 'Candidate-only Inverse FFT' in SOURCE

def test_frame_lock_base_retained():
    assert '_render_current_image_atomically' in SOURCE
