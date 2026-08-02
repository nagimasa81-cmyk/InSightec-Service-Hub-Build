import numpy as np
from core.hybrid_compensation import detect_artifacts


def _noise(shape=(128,128), seed=91):
    rng=np.random.default_rng(seed)
    return rng.normal(0,1,shape)+1j*rng.normal(0,1,shape)


def test_spike_v2_finds_isolated_off_centre_outlier():
    k=_noise()
    k[19,103]+=350+220j
    r=detect_artifacts(k,'Spike',3.2)
    assert r.stats['detector_version']in {'mri_auto_detection_v4','mri_auto_detection_v5'}
    assert np.any(r.mask[17:22,101:106])
    assert r.stats['counts']['spike']>0
    assert len(r.stats['spike_candidates'])>=1


def test_spike_v2_rejects_broad_normal_bright_region():
    k=_noise(seed=92)
    k[20:35,80:95]+=40
    r=detect_artifacts(k,'Spike',3.2)
    assert np.count_nonzero(r.mask[18:37,78:97]) == 0


def test_block_v2_finds_compact_dense_rectangle():
    k=_noise(seed=93)
    k[20:27,91:101]+=80+25j
    r=detect_artifacts(k,'Block',3.0)
    assert np.any(r.mask[18:29,89:103])
    assert r.stats['counts']['block']>=20
    assert len(r.stats['block_candidates'])>=1
    assert r.stats['block_candidates'][0]['fill'] >= 0.48


def test_block_v2_rejects_thin_line_and_centre():
    k=_noise(seed=94)
    k[11,20:110]+=100
    k[58:70,58:70]+=500
    r=detect_artifacts(k,'Block',3.0)
    assert not np.any(r.mask[59:69,59:69])
    assert np.count_nonzero(r.mask[9:14,18:112]) == 0


def test_auto_v4_reports_candidate_metrics():
    k=_noise(seed=95)
    k[17,108]+=400
    k[94:100,18:25]+=70
    r=detect_artifacts(k,'Auto',3.0)
    assert 'adaptive_thresholds' in r.stats
    assert 'spike_candidates' in r.stats
    assert 'block_candidates' in r.stats
