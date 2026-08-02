import numpy as np
from core.auto_correct import auto_correct

def test_auto_correct_keeps_clean_data_unchanged():
    y,x=np.indices((64,64)); k=np.exp(-((x-31.5)**2+(y-31.5)**2)/80.0).astype(complex)
    r=auto_correct(k, protection=95, detail=90)
    assert r.kspace.shape==k.shape
    assert len(r.selected_types) <= 2
    assert np.mean(np.abs(r.kspace-k)) < 0.15

def test_auto_correct_api_metrics():
    k=np.zeros((64,64),complex); k[12,18]=100; k[-13,-19]=100
    r=auto_correct(k, removal=80, protection=60)
    for key in ('artifact_reduction','detail_preservation','overall_quality','mask_pixels'):
        assert key in r.metrics
