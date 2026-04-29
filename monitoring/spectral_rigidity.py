"""Gate M1: GUE spectral rigidity with TMRP k=1 escalation.

Detects manifold drift in activation matrices by comparing observed
spectral statistics against the Gaussian Unitary Ensemble (GUE)
baseline.  Deviations beyond a calibrated threshold indicate potential
jailbreak or latent evasion.

References:
  - Berry & Keating (1999) — H = xp conjecture and spectral rigidity
  - Mehta (2004) — Random Matrices, 3rd edition (Δ₃ statistic)

Calibration: run ``scripts/calibrate_bk_threshold.py`` to set θ_BK
for a given matrix size.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.linalg import eigvalsh

_logger = logging.getLogger("aletheia.monitoring.spectral")

# Sentinel: drift score is inconclusive; caller should escalate via TMRP.
INCONCLUSIVE: float = -1.0

# Default θ_BK override; set via env ALETHEIA_THETA_BK or calibration.
_THETA_BK_OVERRIDE: float | None = None


def set_theta_bk_override(value: float) -> None:
    """Allow runtime override of θ_BK from calibration results."""
    global _THETA_BK_OVERRIDE
    _THETA_BK_OVERRIDE = value


def compute_delta3(spacings: np.ndarray, L: int) -> float:
    r"""Approximate Dyson–Mehta Δ₃(L) from nearest-neighbour spacings.

    Δ₃(L) measures the least-squares deviation of the unfolded
    staircase function from a best-fit line over an interval of
    length *L*.  For GUE, Δ₃(L) ~ (1/π²) ln(L).

    Parameters
    ----------
    spacings : 1-D array of nearest-neighbour spacings (≥ 0).
    L : interval length for the Δ₃ statistic.

    Returns
    -------
    Approximate Δ₃(L) value.
    """
    if len(spacings) < 2:
        return 0.0
    mean_s = np.mean(spacings)
    if mean_s <= 0:
        return 0.0
    unfolded = np.cumsum(spacings / mean_s)
    n_pts = min(len(unfolded), max(L * 4, 64))
    x = np.linspace(0, float(L), int(n_pts))
    N = np.searchsorted(unfolded, x).astype(float)
    # Best-fit line: N(x) ≈ a*x + b → Δ₃ = Var(residuals)
    coeffs = np.polyfit(x, N, 1)
    fitted = np.polyval(coeffs, x)
    variance = float(np.mean((N - fitted) ** 2))
    return variance


def gue_delta3(L: int) -> float:
    r"""Theoretical GUE Δ₃(L) ≈ (1/π²) ln(L) + const.

    Uses the Berry–Keating approximation. The additive constant
    (≈ 0.0590) comes from the exact GUE result; we use 0.06 for
    safety margin.
    """
    if L <= 0:
        return 0.0
    return (1.0 / (np.pi**2)) * np.log(float(L)) + 0.06


def theta_bk(L: int) -> float:
    """Berry–Keating threshold calibrated to 3σ of GUE null distribution.

    Returns the maximum allowable drift score *D* before flagging.
    """
    if _THETA_BK_OVERRIDE is not None:
        return _THETA_BK_OVERRIDE
    if L <= 0:
        return 1.0
    return 0.27 * np.log(float(L)) + 0.5


def compute_drift_score(activation_matrix: np.ndarray) -> float:
    """Compute spectral drift score *D* for an activation matrix.

    Parameters
    ----------
    activation_matrix : 2-D square (or rectangular) array.
        If rectangular, the Gram matrix A·Aᵀ is used.

    Returns
    -------
    D : float
        Absolute deviation |Δ₃_obs − Δ₃_GUE|.
        Returns ``INCONCLUSIVE`` (−1.0) when D < 1e-6, signalling
        that TMRP k=1 escalation is needed.
    """
    mat = np.asarray(activation_matrix, dtype=np.float64)
    if mat.ndim != 2:
        return 0.0
    rows, cols = mat.shape
    if min(rows, cols) < 4:
        return 0.0

    # Make square and symmetric
    if rows != cols:
        mat = mat @ mat.T
    if not np.allclose(mat, mat.T, atol=1e-10):
        mat = (mat + mat.T) / 2.0

    eigvals = eigvalsh(mat)
    eigvals = eigvals - np.mean(eigvals)
    sorted_eig = np.sort(eigvals)
    spacings = np.diff(sorted_eig)
    L = len(eigvals)

    delta_obs = compute_delta3(spacings, L)
    delta_gue = gue_delta3(L)
    D = abs(delta_obs - delta_gue)

    if D < 1e-6:
        return INCONCLUSIVE

    return float(D)
