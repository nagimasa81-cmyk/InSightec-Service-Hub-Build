from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def test_commit_version_metadata():
    text = (ROOT / "version.json").read_text(encoding="utf-8")
    assert '"commit": "0110"' in text
    assert '"version": "5.39.0"' in text


def test_blob_detector_finds_offcentre_blob():
    from core.auto_correct import _bright_blob_mask
    k = np.ones((96, 96), dtype=np.complex128)
    k[15:22, 68:76] = 250.0
    mask = _bright_blob_mask(k, 0.7, 0.6)
    assert mask.shape == k.shape
    assert np.count_nonzero(mask[14:23, 67:77]) > 0
    assert not mask[48, 48]


def test_session_status_and_mask_handoff_are_present():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "def _update_compensation_session_status" in app
    assert "Editable original RAW with retained mask" in app
    assert "Mask {regions} region(s), {pixels} pixels" in app
