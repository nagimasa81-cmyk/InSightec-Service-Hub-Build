import numpy as np
from core.roi_raw_compensation import build_manual_mask_detection, apply_roi_background_compensation

def test_manual_line_is_replaced_from_local_neighbours():
    raw=np.ones((32,32),dtype=np.complex128)
    raw[14:18,8:24]=50+0j
    mask=np.zeros(raw.shape,bool); mask[14:18,8:24]=True
    det,b=build_manual_mask_detection(raw,mask)
    out,st=apply_roi_background_compensation(raw,*b,det,strength=1.0,return_stats=True)
    assert np.mean(np.abs(out[mask])) < 5
    assert st['max_abs_delta'] > 40

def test_only_mask_and_conjugate_partner_change():
    raw=np.ones((16,16),dtype=np.complex128)
    raw[3,4]=20
    mask=np.zeros(raw.shape,bool); mask[3,4]=True
    det,b=build_manual_mask_detection(raw,mask)
    out=apply_roi_background_compensation(raw,*b,det,strength=1.0)
    assert abs(out[3,4]) < 3
