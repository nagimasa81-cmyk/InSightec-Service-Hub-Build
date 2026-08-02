import numpy as np

from core.roi_raw_compensation import (
    apply_roi_background_compensation,
    build_manual_mask_detection,
)


def test_high_background_model_is_three_pass_and_95_to_100_percent_replacement():
    raw = np.ones((48, 48), dtype=np.complex128)
    raw[20:28, 8:40] = 50 + 10j
    mask = np.zeros(raw.shape, dtype=bool)
    mask[21:27, 10:38] = True
    detection, bounds = build_manual_mask_detection(
        raw,
        mask,
        mask_expand=3,
        donor_halo=5,
        model_passes=3,
        stripe_suppression=0.85,
        edge_blend=True,
    )
    corrected, stats = apply_roi_background_compensation(
        raw, *bounds, detection, strength=1.0, return_stats=True
    )
    assert detection.stats["background_model"] is True
    assert detection.stats["model_passes"] == 3
    assert detection.stats["stripe_suppression"] == 0.85
    assert detection.stats["edge_blend"] is True
    assert stats["after_mean"] < stats["before_mean"] * 0.20
    # Background should remain unchanged outside the expanded correction region.
    assert corrected[0, 0] == raw[0, 0]


def test_high_reduces_horizontal_and_vertical_band_energy():
    raw = np.ones((64, 64), dtype=float)
    raw[26:34, :] = 30.0
    raw[:, 28:36] += 20.0
    mask = np.zeros_like(raw, dtype=bool)
    mask[24:36, 20:44] = True
    detection, bounds = build_manual_mask_detection(
        raw,
        mask,
        mask_expand=3,
        donor_halo=5,
        model_passes=3,
        stripe_suppression=0.85,
        edge_blend=True,
    )
    corrected = apply_roi_background_compensation(raw, *bounds, detection, strength=1.0)
    y0, y1, x0, x1 = bounds
    before = np.mean(np.abs(raw[y0:y1, x0:x1][detection.mask]))
    after = np.mean(np.abs(corrected[y0:y1, x0:x1][detection.mask]))
    assert after < before * 0.25
