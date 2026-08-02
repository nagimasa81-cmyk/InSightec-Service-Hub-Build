from pathlib import Path
import numpy as np
from core.roi_raw_compensation import build_manual_mask_detection, apply_roi_background_compensation


def test_manual_mask_only_changes_painted_region_and_conjugate_partner():
    raw = np.ones((32, 32), dtype=np.complex128)
    raw[8:12, 20:24] = 100 + 20j
    mask = np.zeros(raw.shape, dtype=bool)
    mask[9:11, 21:23] = True
    detection, bounds = build_manual_mask_detection(raw, mask)
    y0, y1, x0, x1 = bounds
    out, stats = apply_roi_background_compensation(raw, y0, y1, x0, x1, detection, return_stats=True)
    assert stats["changed"] == 4
    assert np.max(np.abs(out[9:11, 21:23])) < np.max(np.abs(raw[9:11, 21:23]))
    assert out.shape == raw.shape


def test_commit0085c_source_contains_manual_paint_and_spike_transfer():
    source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "manual_mask_enabled" in source
    assert "Start Manual Paint on Raw Data" in source
    assert "Spike Diag loaded the current Image Workspace image" in source
