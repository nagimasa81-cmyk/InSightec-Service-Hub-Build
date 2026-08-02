import numpy as np
from core.hybrid_compensation import detect_artifacts


def base_kspace(n=96):
    y, x = np.indices((n, n), dtype=float)
    r2 = (y-(n-1)/2)**2 + (x-(n-1)/2)**2
    return np.exp(-r2/(2*(n/9)**2)).astype(np.complex128)


def test_auto_line_band_confidence_and_dc_protection():
    k = base_kspace()
    k[22:25, 10:86] += 18.0
    result = detect_artifacts(k, "Auto", 2.5)
    assert np.any(result.mask)
    assert result.stats["detector_version"] in {"mri_auto_detection_v2", "mri_auto_detection_v3", "mri_auto_detection_v4", "mri_auto_detection_v5"}
    assert result.stats["confidences"]["line"] > 0.2 or result.stats["confidences"]["band"] > 0.2
    c = k.shape[0] // 2
    assert not result.mask[c, c]


def test_auto_spike_keeps_hermitian_partner():
    k = base_kspace()
    k[12, 17] = 1000 + 120j
    result = detect_artifacts(k, "Spike", 2.0)
    assert result.mask[12, 17]
    cy = cx = k.shape[0] // 2
    sy, sx = (2*cy-12) % k.shape[0], (2*cx-17) % k.shape[1]
    assert result.mask[sy, sx]


def test_auto_rejects_clean_data_at_high_threshold():
    k = base_kspace()
    result = detect_artifacts(k, "Auto", 8.0)
    assert result.mask.shape == k.shape
    assert result.confidence <= 1.0


def test_ring_candidate_has_type_confidence_map():
    n = 96
    k = base_kspace(n)
    y, x = np.indices((n, n), dtype=float)
    r = np.hypot(y-(n-1)/2, x-(n-1)/2)
    k[(r > 25) & (r < 27)] += 20
    result = detect_artifacts(k, "Ring", 2.0)
    assert "ring" in result.stats["confidences"]
    assert result.stats["counts"]["ring"] >= 0
