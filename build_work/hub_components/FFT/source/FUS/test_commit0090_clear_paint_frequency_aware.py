from pathlib import Path
import numpy as np

from core.hybrid_compensation import _frequency_aware_weight, compensate


def test_clear_paint_replaces_mask_and_hides_overlay():
    source = Path('app.py').read_text(encoding='utf-8')
    assert 'self.manual_mask = np.zeros(shape, dtype=bool)' in source
    assert 'self.manual_mask_item.hide()' in source
    assert 'self.plot.viewport().update()' in source
    assert 'self.open_comp_comparison_button.setEnabled(False)' in source
    assert 'self.compensation_difference_fft = None' in source


def test_frequency_aware_model_protects_dc_and_reports_bands():
    rows = cols = 64
    yy, xx = np.indices((rows, cols))
    radius = np.hypot(yy - 31.5, xx - 31.5)
    kspace = np.exp(-(radius / 8.0) ** 2).astype(np.complex128)
    mask = np.zeros((rows, cols), dtype=bool)
    mask[8:12, :] = True
    kspace[mask] += 20.0
    weight, report = _frequency_aware_weight(kspace, mask, 'Horizontal', 'High')
    assert weight.shape == kspace.shape
    assert 0.0 < report['dc_weight'] < 0.6
    assert report['high_band_gain'] >= 0.45
    assert 0.0 < report['mean_mask_weight'] <= 1.0


def test_frequency_aware_compensation_metadata_and_effect():
    kspace = np.zeros((48, 48), dtype=np.complex128)
    kspace[23:25, 23:25] = 100.0
    mask = np.zeros_like(kspace, dtype=bool)
    mask[8:11, :] = True
    kspace[mask] = 15.0 + 2.0j
    result = compensate(
        kspace, mask, artifact_type='Band', level='High',
        frequency_aware=True, harmonic_poisson=True,
        multi_pass=True, hermitian_symmetry=True,
    )
    assert result.metadata['frequency_model'] == 'adaptive_three_band_directional_v2'
    assert set(result.metadata['frequency_band_gains']) >= {
        'low_band_gain', 'mid_band_gain', 'high_band_gain', 'dc_weight', 'mean_mask_weight'
    }
    assert np.mean(np.abs(result.kspace[result.mask])) < np.mean(np.abs(kspace[result.mask]))
