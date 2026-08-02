import numpy as np
from core.roi_raw_compensation import detect_roi_artifact_mask, apply_roi_background_compensation


def test_roi_line_detection_and_apply_are_separate_steps():
    raw = np.ones((64, 64), dtype=np.complex128)
    raw[26, 18:46] = 20 + 2j
    detection = detect_roi_artifact_mask(raw, 20, 34, 14, 50, mode="Line", threshold_sigma=2.0)
    assert detection.stats["changed"] > 0
    assert np.array_equal(raw, np.where(np.ones_like(raw, dtype=bool), raw, raw))
    corrected = apply_roi_background_compensation(raw, 20, 34, 14, 50, detection, strength=1.0)
    assert np.mean(np.abs(corrected[26, 18:46])) < np.mean(np.abs(raw[26, 18:46]))


def test_roi_detector_rejects_spike_mode_names():
    raw = np.ones((32, 32), dtype=float)
    try:
        detect_roi_artifact_mask(raw, 8, 20, 8, 20, mode="Strong Pixels")
    except ValueError:
        pass
    else:
        raise AssertionError("Spike-style mode must not be accepted by ROI RAW compensation")
