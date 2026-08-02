import numpy as np
from core.hybrid_compensation import detect_artifacts, compensate


def _smooth_kspace(n=128):
    y, x = np.indices((n, n), dtype=float)
    r2 = (y-(n-1)/2)**2 + (x-(n-1)/2)**2
    return (120*np.exp(-r2/(2*(n/8.5)**2))).astype(np.complex128)


def test_conservative_auto_rejects_more_normal_signal_than_sensitive():
    k = _smooth_kspace()
    # Add a valid compact block while preserving a broad smooth image-forming core.
    k[23:30, 91:101] += 35 + 8j
    conservative = detect_artifacts(k, 'Auto', 3.0, 'Conservative')
    sensitive = detect_artifacts(k, 'Auto', 3.0, 'Sensitive')
    assert conservative.stats['auto_sensitivity'] == 'Conservative'
    assert conservative.stats['normal_signal_guard_pixels'] > 0
    assert np.count_nonzero(conservative.mask) <= np.count_nonzero(sensitive.mask)
    c = k.shape[0] // 2
    assert not conservative.mask[c, c]


def test_advanced_overrides_are_reported_and_preservation_reduces_change():
    k = _smooth_kspace(96)
    mask = np.zeros(k.shape, dtype=bool)
    mask[33:38, 63:70] = True
    low_preserve = compensate(
        k, mask, artifact_type='Manual Only', level='High',
        mask_expansion=0, donor_halo=2, pass_count=1,
        strength_override=0.80, structure_preservation=0.0,
    )
    high_preserve = compensate(
        k, mask, artifact_type='Manual Only', level='High',
        mask_expansion=0, donor_halo=2, pass_count=1,
        strength_override=0.80, structure_preservation=0.90,
    )
    assert high_preserve.metadata['mask_expansion'] == 0
    assert high_preserve.metadata['donor_halo'] == 2
    assert high_preserve.metadata['passes'] == 1
    assert high_preserve.metadata['strength'] == 0.80
    assert high_preserve.metadata['structure_preservation'] == 0.90
    assert np.sum(high_preserve.difference_fft) <= np.sum(low_preserve.difference_fft)


def test_advanced_gui_controls_are_wired_in_source():
    text = open('app.py', encoding='utf-8').read()
    for token in (
        'Advanced Compensation Tuning', 'Auto Mask sensitivity',
        'Normal signal preservation', 'Reset Advanced Settings',
        'mask_expansion=', 'structure_preservation=',
        'detection_sensitivity=',
    ):
        assert token in text
    # Use Painted Mask remains in one row with Clear Paint; it must not be
    # re-added later as a standalone widget.
    assert text.count('comp_layout.addWidget(self.detect_comp_button)') == 0
