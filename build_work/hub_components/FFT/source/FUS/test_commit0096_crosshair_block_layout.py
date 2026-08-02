from pathlib import Path
import numpy as np
from core.hybrid_compensation import detect_artifacts
APP=Path('app.py').read_text(encoding='utf-8')

def test_crosshair_visibility_tracks_profile_curtain():
    block=APP[APP.index('def _profile_curtain_toggled'):APP.index('def _enforce_profile_curtain_geometry')]
    assert 'panel._set_crosshair_visible(bool(expanded))' in block
    assert 'self.primary_panel._set_crosshair_visible(False)' in APP

def test_clear_paint_is_beside_use_mask():
    assert 'use_mask_row.addWidget(self.detect_comp_button, 1)' in APP
    assert 'use_mask_row.addWidget(self.comp_clear_mask_button)' in APP

def test_fragmented_rectangular_lobes_detect_as_block():
    a=np.zeros((128,128),dtype=np.complex128)
    rng=np.random.default_rng(4)
    a += (rng.normal(0,0.03,a.shape)+1j*rng.normal(0,0.03,a.shape))
    # symmetric fragmented bars like the supplied screenshot
    for y in (36,43,84,91):
        for x0,x1 in ((18,31),(38,49),(56,68),(76,88),(95,109)):
            a[y:y+4,x0:x1]+=8.0
    r=detect_artifacts(a,'block')
    assert r.stats['counts']['block'] >= 80
    assert len(r.stats['block_candidates']) >= 2
