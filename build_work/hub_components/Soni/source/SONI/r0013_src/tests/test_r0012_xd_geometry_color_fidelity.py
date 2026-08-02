from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src" / "ui" / "main_window.py"

def test_release_metadata():
    assert (ROOT / "VERSION").read_text().strip() in {"RC2-R0013", "RC2-R0014"}
    text = (ROOT / "version.json").read_text()
    assert any(x in text for x in ('"commit": "R0013"', '"commit": "R0014"'))

def test_xd_has_geometry_derived_guides_and_scale_modes():
    text = MAIN.read_text()
    assert "_ring_radii" in text
    assert "_sector_angles" in text
    assert '["Adaptive", "Manual", "Normalized"]' in text
    assert "self.gamma" in text
    assert "np.percentile(finite, 1.0)" in text

def test_sdr_fixed_scale_except_manual():
    text = MAIN.read_text()
    assert 'self.parameter == "Element SDR" and self.scale_mode != "Manual"' in text
    assert "lo, hi = 0.0, 1.0" in text
