import numpy as np

from core.hybrid_compensation import compensate, detect_artifacts


def _diagonal_kspace(angle: float, n: int = 128) -> np.ndarray:
    rng = np.random.default_rng(95)
    data = rng.normal(0.0, 0.05, (n, n)).astype(np.complex128)
    cy = cx = (n - 1.0) / 2.0
    theta = np.deg2rad(angle)
    for t in np.linspace(-46.0, 46.0, 19):
        x = int(round(cx + t * np.cos(theta)))
        y = int(round(cy + t * np.sin(theta)))
        if 0 <= y < n and 0 <= x < n:
            radius = np.hypot((y - cy) / (n / 2.0), (x - cx) / (n / 2.0))
            if radius > 0.12:
                data[y, x] += 18.0 + 2.0j
    return data


def test_detects_diagonal_spike_train_and_angle():
    source = _diagonal_kspace(45.0)
    result = detect_artifacts(source, "Diagonal", 4.0)
    assert result.confidence >= 0.58
    assert result.stats["counts"]["diagonal"] > 0
    assert result.stats["diagonal_candidates"]
    assert abs(result.stats["diagonal_angle_degrees"] - 45.0) <= 5.0
    assert result.direction.startswith("Diagonal")


def test_auto_mode_can_select_diagonal_artifact():
    result = detect_artifacts(_diagonal_kspace(135.0), "Auto", 4.0)
    assert "diagonal" in result.stats["selected_types"]
    assert result.stats["confidences"]["diagonal"] >= 0.58


def test_random_texture_does_not_create_diagonal_mask():
    rng = np.random.default_rng(951)
    source = rng.normal(0.0, 1.0, (128, 128)).astype(np.complex128)
    result = detect_artifacts(source, "Diagonal", 4.0)
    assert result.stats["counts"]["diagonal"] == 0
    assert result.confidence == 0.0


def test_frequency_aware_compensation_accepts_diagonal_direction():
    source = _diagonal_kspace(35.0)
    detection = detect_artifacts(source, "Diagonal", 4.0)
    result = compensate(source, detection.mask, artifact_type="Diagonal", level="High")
    assert result.metadata["direction"].startswith("Diagonal")
    assert np.isfinite(result.image).all()
    assert result.metrics["changed_pixels"] > 0
