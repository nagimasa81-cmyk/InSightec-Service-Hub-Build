import numpy as np

from core.raw_compensation import compensate_roi_to_background


def _synthetic_kspace(size=96):
    rng = np.random.default_rng(85)
    data = rng.normal(0, 0.7, (size, size)) + 1j * rng.normal(0, 0.7, (size, size))
    # Strong vertical and horizontal signals inside the test ROI.
    data[28:68, 44] += 35 + 8j
    data[51, 28:68] += 28 - 5j
    data[38, 37] += 60 + 20j
    return data


def test_hybrid_compensation_flattens_strong_roi_signal():
    source = _synthetic_kspace()
    result, stats = compensate_roi_to_background(
        source, 28, 68, 28, 68,
        strength=1.0,
        mode="Hybrid (Spikes + Lines)",
        threshold_sigma=2.5,
        target_ratio=1.0,
        return_stats=True,
    )
    before = np.abs(source[28:68, 28:68])
    after = np.abs(result[28:68, 28:68])
    assert stats["changed"] > 0
    assert stats["line_rows"] > 0 or stats["line_cols"] > 0
    assert float(after.max()) < float(before.max())
    assert result.shape == source.shape


def test_compensation_does_not_flatten_unselected_area():
    source = _synthetic_kspace()
    result = compensate_roi_to_background(
        source, 28, 68, 28, 68,
        strength=0.8,
        mode="Strong Pixels",
        threshold_sigma=3.0,
        target_ratio=1.0,
    )
    # A corner far from both ROI and conjugate partner remains unchanged.
    assert result[3, 4] == source[3, 4]


def test_target_ratio_controls_replacement_level():
    source = _synthetic_kspace()
    low, _ = compensate_roi_to_background(
        source, 28, 68, 28, 68, 1.0,
        mode="Hybrid (Spikes + Lines)", threshold_sigma=2.5,
        target_ratio=0.75, return_stats=True,
    )
    high, _ = compensate_roi_to_background(
        source, 28, 68, 28, 68, 1.0,
        mode="Hybrid (Spikes + Lines)", threshold_sigma=2.5,
        target_ratio=1.50, return_stats=True,
    )
    # A higher target background should preserve more total ROI magnitude.
    assert np.mean(np.abs(high[28:68, 28:68])) >= np.mean(np.abs(low[28:68, 28:68]))


def test_integer_input_is_promoted_instead_of_truncated():
    source = np.ones((64, 64), dtype=np.int16)
    source[20:44, 31] = 100
    result = compensate_roi_to_background(
        source, 20, 44, 20, 44,
        strength=0.65,
        mode="Line Signals",
        threshold_sigma=2.0,
        target_ratio=1.0,
    )
    assert np.issubdtype(result.dtype, np.floating)


def test_nonfinite_input_is_rejected_explicitly():
    source = _synthetic_kspace(64)
    source[10, 10] = np.nan + 0j
    with np.testing.assert_raises_regex(ValueError, "NaN or infinite"):
        compensate_roi_to_background(source, 16, 48, 16, 48)


def test_conjugate_partner_is_written_from_stable_snapshot():
    size = 96
    source = _synthetic_kspace(size)
    result, stats = compensate_roi_to_background(
        source, 28, 68, 28, 68,
        strength=1.0,
        mode="Hybrid (Spikes + Lines)",
        threshold_sigma=2.5,
        target_ratio=1.0,
        return_stats=True,
    )
    assert stats["changed"] > 0
    cy = cx = size // 2
    # Check Hermitian pairing for the deliberately strong isolated sample.
    y, x = 38, 37
    sy, sx = (2 * cy - y) % size, (2 * cx - x) % size
    assert np.allclose(result[sy, sx], np.conj(result[y, x]))
