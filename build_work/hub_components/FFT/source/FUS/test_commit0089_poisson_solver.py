import numpy as np
from core.hybrid_compensation import _poisson_fill, compensate


def test_guided_poisson_preserves_known_samples_and_fills_mask():
    yy, xx = np.indices((33, 35), dtype=float)
    guidance = (0.4 * xx + 0.7 * yy) + 1j * (0.2 * xx - 0.1 * yy)
    source = guidance.copy()
    mask = np.zeros(source.shape, dtype=bool)
    mask[10:23, 11:25] = True
    source[mask] = 5000 + 5000j
    solved, report = _poisson_fill(
        source, mask, guidance=guidance, iterations=1200, omega=1.7, tolerance=1e-8
    )
    assert np.array_equal(solved[~mask], source[~mask])
    assert np.max(np.abs(solved[mask] - guidance[mask])) < 1e-3
    assert report["converged"] == 1.0
    assert report["residual"] <= 1e-8


def test_commit0089_compensation_reports_real_poisson_solver():
    rng = np.random.default_rng(89)
    source = rng.normal(size=(40, 42)) + 1j * rng.normal(size=(40, 42))
    mask = np.zeros(source.shape, dtype=bool)
    mask[18:22, 5:37] = True
    source[mask] += 80.0
    result = compensate(
        source, mask=mask, artifact_type="Band", level="High",
        harmonic_poisson=True, multi_pass=True, hermitian_symmetry=True,
    )
    assert result.metadata["poisson_solver"] == "guided_red_black_sor"
    assert len(result.metadata["poisson_iterations"]) == 3
    assert len(result.metadata["poisson_residuals"]) == 3
    assert np.all(np.isfinite(result.kspace))
    assert result.metrics["after_mean"] < result.metrics["before_mean"]
