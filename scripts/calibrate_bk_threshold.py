#!/usr/bin/env python3
"""Calibrate θ_BK threshold using empirical GUE surrogates.

Generates random GUE matrices (null hypothesis: no drift), computes
drift scores, and reports the threshold at a given false-positive
rate.

Usage:
    python scripts/calibrate_bk_threshold.py --size 100 --samples 5000

The recommended threshold can be set via ``ALETHEIA_THETA_BK`` or
injected into the runtime with
``monitoring.spectral_rigidity.set_theta_bk_override(value)``.
"""
from __future__ import annotations

import sys

import click
import numpy as np

# Allow running from repo root
sys.path.insert(0, ".")

from monitoring.spectral_rigidity import compute_drift_score


@click.command()
@click.option("--size", default=100, help="Matrix dimension (NxN).")
@click.option("--samples", default=5000, help="Number of GUE samples.")
@click.option(
    "--fpr",
    default=1e-6,
    type=float,
    help="Target false-positive rate (default: 1e-6).",
)
def main(size: int, samples: int, fpr: float) -> None:
    """Calibrate Berry–Keating threshold from GUE null distribution."""
    click.echo(f"Generating {samples} GUE matrices of size {size}×{size}…")

    rng = np.random.default_rng(42)
    scores: list[float] = []

    for i in range(samples):
        # Generate GUE matrix: Hermitian with i.i.d. complex Gaussian entries
        g = rng.standard_normal((size, size)) + 1j * rng.standard_normal((size, size))
        gue = (g + g.conj().T) / 2.0
        score = compute_drift_score(gue.real)
        # Skip inconclusive scores (they would trigger escalation)
        if score >= 0:
            scores.append(score)

        if (i + 1) % 500 == 0:
            click.echo(f"  {i + 1}/{samples} done")

    if not scores:
        click.echo("ERROR: No valid scores produced.", err=True)
        sys.exit(1)

    scores_arr = np.array(scores)
    percentile = (1.0 - fpr) * 100.0

    threshold = float(np.percentile(scores_arr, percentile))
    click.echo(f"\nResults for matrix size N={size}:")
    click.echo(f"  Samples:    {len(scores)}")
    click.echo(f"  Mean D:     {scores_arr.mean():.6f}")
    click.echo(f"  Std D:      {scores_arr.std():.6f}")
    click.echo(f"  Max D:      {scores_arr.max():.6f}")
    click.echo(f"  Target FPR: {fpr:.2e}")
    click.echo(f"  Percentile: {percentile:.4f}%")
    click.echo(f"\n  Recommended θ_BK = {threshold:.6f}")
    click.echo(
        f"\nTo apply: export ALETHEIA_THETA_BK={threshold:.6f}\n"
        f"Or call: set_theta_bk_override({threshold:.6f})"
    )


if __name__ == "__main__":
    main()
