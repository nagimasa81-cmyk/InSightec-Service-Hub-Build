from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_commit0116_version():
    text=(ROOT/'app.py').read_text(encoding='utf-8')
    assert 'Commit0116 Detection Rollback and Crosshair Safety' in text


def test_detection_matches_commit0114_reference():
    import hashlib
    current=(ROOT/'core'/'auto_correct.py').read_bytes()
    assert hashlib.sha256(current).hexdigest() == 'da920aa93848df2d46e0f5282486a90892d12740973b00397bee3aedd3c602bc'


def test_commit0115_geometry_override_removed():
    text=(ROOT/'core'/'auto_correct.py').read_text(encoding='utf-8')
    assert '_blob_mask_geometry' not in text
    assert 'paired_edge_blob' not in text
    assert 'centre-axis bridge' not in text


def test_crosshair_safety_retained():
    text=(ROOT/'app.py').read_text(encoding='utf-8')
    assert 'self.hline.hide(); self.vline.hide()' in text
    assert 'self.sync_cursor_check.setChecked(False)' in text


def test_safer_high_extreme_presets_retained():
    text=(ROOT/'app.py').read_text(encoding='utf-8')
    assert '"High": {"strength": 0.92, "mask_expand": 2' in text
    assert '"Extreme": {"strength": 0.98, "mask_expand": 3' in text
