"""Static regression tests for Commit0071 source packaging.

These tests intentionally avoid importing Qt so they can run in lightweight CI
source validation jobs before the Windows GUI build environment is installed.
"""
from pathlib import Path

SOURCE = Path(__file__).with_name("app.py").read_text(encoding="utf-8")


def test_commit_version_marker():
    assert "Commit0071" in SOURCE


def test_candidate_families_present():
    for marker in ('"type":"point"', '"type":"oblique"', '"type":"band"'):
        assert marker in SOURCE


def test_inverse_fft_validation_present():
    assert "wave_complex = ifft2c(component_k)" in SOURCE
    assert "predicted_wave_angle" in SOURCE
    assert "predicted_period" in SOURCE


def test_intersection_not_required():
    assert "do not require an intersection" in SOURCE


def test_no_delayed_second_fit():
    assert "QTimer.singleShot(0, self._apply_default_image_geometry)" not in SOURCE


def test_compact_frequency_marker():
    assert "paired chevron" in SOURCE
    assert "min(rows, cols) * 0.014" in SOURCE
