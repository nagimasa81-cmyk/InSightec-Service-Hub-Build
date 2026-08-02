from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
AUTO = (ROOT / 'core' / 'auto_correct.py').read_text(encoding='utf-8')


def test_all_image_panels_hide_crosshair_on_creation():
    assert 'self.hline.hide(); self.vline.hide()' in APP
    assert 'self.sync_cursor_check.setChecked(False)' in APP


def test_high_extreme_do_not_use_legacy_aggressive_line_settings():
    assert '"High": {"strength": 0.92, "mask_expand": 2, "donor_halo": 4, "model_passes": 2, "stripe_suppression": 0.35' in APP
    assert '"Extreme": {"strength": 0.98, "mask_expand": 3, "donor_halo": 5, "model_passes": 3, "stripe_suppression": 0.55' in APP


def test_blob_geometry_and_axis_guard_are_present():
    assert 'def _blob_mask_geometry' in AUTO
    assert 'paired_edge_blob' in AUTO
    assert 'axis_fraction' in AUTO
    assert 'centre-axis bridge' in AUTO


def test_edge_pair_geometry_prefers_edges_and_not_centre_axis():
    from core.auto_correct import _blob_mask_geometry
    mask = np.zeros((128, 128), dtype=bool)
    mask[25:45, 0:10] = True
    mask[83:103, -10:] = True
    g = _blob_mask_geometry(mask)
    assert g['edge_fraction'] > 0.9
    assert g['axis_fraction'] < 0.1
    assert g['pair_support'] > 0.8
