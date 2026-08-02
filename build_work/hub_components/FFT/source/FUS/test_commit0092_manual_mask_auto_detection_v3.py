import numpy as np

from core.hybrid_compensation import detect_artifacts


def test_auto_detection_never_masks_dc_core():
    shape = (128, 128)
    yy, xx = np.indices(shape)
    cy, cx = (shape[0]-1)/2, (shape[1]-1)/2
    # Deliberately extreme but normal-looking central low-frequency energy.
    k = np.zeros(shape, dtype=np.complex128)
    core = np.hypot((yy-cy)/(shape[0]/2), (xx-cx)/(shape[1]/2)) < 0.08
    k[core] = 1e6
    result = detect_artifacts(k, "Auto", 4.0)
    assert not np.any(result.mask[core])
    assert result.stats["detector_version"] in {"mri_auto_detection_v4", "mri_auto_detection_v5"}
    assert result.stats["centre_guard_radius"] == 0.10


def test_auto_detection_finds_off_centre_band_but_keeps_centre_clear():
    rng = np.random.default_rng(8)
    k = rng.normal(size=(128, 128)) + 1j*rng.normal(size=(128, 128))
    k[23:26, :] += 80
    result = detect_artifacts(k, "Auto", 3.0)
    assert np.count_nonzero(result.mask[20:30]) > 0
    cy, cx = 64, 64
    assert not np.any(result.mask[cy-5:cy+6, cx-5:cx+6])


def test_manual_ui_modes_are_present_in_source():
    text = open('app.py', encoding='utf-8').read()
    assert '"Manual Only", "Auto", "Spike", "Line", "Band", "Block", "Ring"' in text
    assert '"Brush", "Line", "Band", "Block", "Ring", "Eraser", "Remove Component"' in text
    assert 'Manual Only mode requires a painted mask' in text
    assert 'elif mode == "Remove Component":' in text
