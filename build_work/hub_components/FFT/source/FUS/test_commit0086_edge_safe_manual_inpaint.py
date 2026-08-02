import numpy as np

from core.roi_raw_compensation import (
    apply_roi_background_compensation,
    build_manual_mask_detection,
)


def test_edge_mask_is_not_dropped_and_does_not_wrap_from_opposite_edge():
    raw = np.ones((12, 12), dtype=np.complex128)
    raw[0, 0] = 80.0
    raw[-1, -1] = 900.0  # must not be treated as a neighbour of (0, 0)
    mask = np.zeros(raw.shape, dtype=bool)
    mask[0, 0] = True

    detection, bounds = build_manual_mask_detection(raw, mask)
    output, stats = apply_roi_background_compensation(
        raw, *bounds, detection, strength=1.0, return_stats=True
    )

    assert abs(output[0, 0]) < 5.0
    assert output[-1, -1] == raw[-1, -1]
    assert stats["changed"] == 1


def test_edge_safe_inpaint_preserves_unpainted_pixels():
    raw = np.arange(100, dtype=float).reshape(10, 10).astype(np.complex128)
    mask = np.zeros(raw.shape, dtype=bool)
    mask[0, 3:7] = True

    detection, bounds = build_manual_mask_detection(raw, mask)
    output = apply_roi_background_compensation(raw, *bounds, detection, strength=1.0)

    untouched = ~mask
    # Conjugate partners may also change by design; all other pixels stay stable.
    cy, cx = raw.shape[0] // 2, raw.shape[1] // 2
    for y, x in zip(*np.where(mask)):
        untouched[(2 * cy - y) % raw.shape[0], (2 * cx - x) % raw.shape[1]] = False
    assert np.array_equal(output[untouched], raw[untouched])


def test_aggressive_high_profile_expands_mask_and_uses_farther_donors():
    raw = np.ones((25, 25), dtype=np.complex128)
    raw[9:16, 9:16] = 100.0
    mask = np.zeros(raw.shape, dtype=bool)
    mask[12, 12] = True

    low, _ = build_manual_mask_detection(raw, mask, mask_expand=0, donor_halo=1)
    high, bounds = build_manual_mask_detection(raw, mask, mask_expand=3, donor_halo=5)
    output = apply_roi_background_compensation(raw, *bounds, high, strength=1.0)

    assert high.stats["changed"] > low.stats["changed"]
    assert high.stats["mask_expand"] == 3
    assert high.stats["donor_halo"] == 5
    assert np.max(np.abs(output[9:16, 9:16])) < 10.0
