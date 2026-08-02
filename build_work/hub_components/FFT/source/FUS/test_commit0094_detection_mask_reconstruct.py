from pathlib import Path
import numpy as np
from core.hybrid_compensation import detect_artifacts

APP = Path('app.py').read_text(encoding='utf-8')


def _noise(seed=42):
    rng=np.random.default_rng(seed)
    return rng.normal(0,0.5,(128,128))+1j*rng.normal(0,0.5,(128,128))


def test_block_v3_finds_moderate_rectangular_region():
    k=_noise()
    k[28:38,82:97]+=8+3j
    r=detect_artifacts(k,'Block',4.0)
    assert r.stats['detector_version']=='mri_auto_detection_v5'
    assert r.stats['counts']['block'] >= 80
    assert r.confidence >= 0.55


def test_vertical_line_requires_long_coherent_support():
    k=_noise(7)
    k[35:70,90]+=7
    short=detect_artifacts(k,'Line',3.5)
    assert short.stats['counts']['line']==0
    k2=_noise(8)
    k2[5:123,90]+=9
    long=detect_artifacts(k2,'Line',3.5)
    assert long.stats['counts']['line'] >= 80


def test_mask_edit_keeps_preview_reconstructable():
    assert 'has_mask = bool(panel is not None and panel.manual_mask is not None and np.any(panel.manual_mask))' in APP
    assert 'self.preview_comp_button.setEnabled(has_mask)' in APP
    assert 'def _rebuild_compensation_detection_from_current_mask' in APP
    preview=APP[APP.index('def preview_compensation'):APP.index('def open_compensation_comparison')]
    assert 'self._rebuild_compensation_detection_from_current_mask()' in preview
    assert 'self.detect_compensation_mask()' not in preview
