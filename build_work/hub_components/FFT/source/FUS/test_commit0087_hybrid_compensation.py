import numpy as np
from core.hybrid_compensation import compensate, detect_artifacts, enforce_hermitian


def synthetic_kspace(n=64):
    y, x = np.indices((n, n))
    image = np.exp(-((x-n/2)**2+(y-n/2)**2)/(2*(n/8)**2))
    k = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(image)))
    return k


def test_auto_detection_and_mask_generation():
    k = synthetic_kspace()
    k[10, 5:55] += 5000
    result = detect_artifacts(k, "Auto", 3.0)
    assert result.mask.shape == k.shape
    assert result.mask.any()
    assert result.artifact_type in {"Spike", "Line", "Band", "Block", "Ring"}


def test_extreme_hybrid_outputs_and_score():
    k = synthetic_kspace()
    mask = np.zeros(k.shape, bool)
    mask[8:12, 6:58] = True
    k2 = k.copy(); k2[mask] += 8000
    result = compensate(k2, mask, artifact_type="Band", level="Extreme")
    assert result.kspace.shape == k.shape
    assert result.difference_fft.shape == k.shape
    assert result.difference_phase.shape == k.shape
    assert result.difference_image.shape == k.shape
    assert result.metadata["passes"] == 5
    assert result.metrics["artifact_reduction_score"] >= 0
    assert np.mean(np.abs(result.kspace[mask])) < np.mean(np.abs(k2[mask]))


def test_hermitian_symmetry_is_preserved():
    k = synthetic_kspace()
    mask = np.zeros(k.shape, bool); mask[7:10, 20:30] = True
    k[mask] += 1000 + 300j
    result = compensate(k, mask, level="High", hermitian_symmetry=True)
    rows, cols = result.kspace.shape; cy, cx = rows//2, cols//2
    ys, xs = np.where(result.mask)
    for y, x in zip(ys[:50], xs[:50]):
        sy, sx = (2*cy-y)%rows, (2*cx-x)%cols
        assert np.allclose(result.kspace[sy, sx], np.conj(result.kspace[y, x]))
