"""TMRP escalation: cross-layer covariance probe.

When the primary spectral drift score is inconclusive (< 1e-6),
this module provides a secondary probe using the matrix-coefficient
analogue — cross-layer covariance between activation snapshots.

This resists accidental averaging across layers and provides
a more robust signal for subtle manifold drift.
"""
from __future__ import annotations

import numpy as np

from monitoring.spectral_rigidity import compute_drift_score


def cross_layer_covariance_probe(activations: list[np.ndarray]) -> float:
    """Compute drift score from the covariance of multiple activation layers.

    Parameters
    ----------
    activations : list of 2-D arrays (one per layer or time step).

    Returns
    -------
    Drift score *D* computed on the cross-layer covariance matrix.
    """
    if len(activations) < 2:
        return 0.0
    flattened = [a.flatten() for a in activations]
    # Pad to same length if needed
    max_len = max(len(f) for f in flattened)
    padded = [np.pad(f, (0, max_len - len(f))) for f in flattened]
    combined = np.stack(padded, axis=0)
    if combined.shape[0] < 4:
        # Pad with noisy copies to get a meaningful covariance matrix
        rng = np.random.default_rng(42)
        while combined.shape[0] < 4:
            noise = combined[-1] + rng.normal(0, 1e-6, combined.shape[1])
            combined = np.vstack([combined, noise[np.newaxis, :]])
    cov_matrix = np.cov(combined)
    return compute_drift_score(cov_matrix)


def temporal_cross_covariance(
    prev_activation: np.ndarray,
    curr_activation: np.ndarray,
) -> float:
    """Covariance-based drift between two consecutive inference steps."""
    return cross_layer_covariance_probe([prev_activation, curr_activation])
