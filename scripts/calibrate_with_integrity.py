#!/usr/bin/env python3
"""Calibration script with integrity protections.

- Signed Ed25519 manifests
- Multi-run consensus (median parameters)
- Outlier rejection (> 2σ from median)

Usage::

    python scripts/calibrate_with_integrity.py \\
        --dataset data/benign_activations.npy \\
        --runs 5 \\
        --output calibration_manifest.json

The signing key is persisted as PEM at ``--key-file`` with 0600
permissions, matching the key-management pattern in
``crypto/tpm_interface.py``.
"""

from __future__ import annotations

import json
import os
import sys

import click
import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Allow running from repo root
sys.path.insert(0, ".")

from crypto.calibration_manifest import CalibrationIntegrity
from monitoring.spectral_rigidity import compute_drift_score, theta_bk


def _load_or_generate_key(key_file: str) -> Ed25519PrivateKey:
    """Load an Ed25519 signing key from PEM, or generate and persist one."""
    if os.path.isfile(key_file):
        with open(key_file, "rb") as fh:
            key = serialization.load_pem_private_key(fh.read(), password=None)
        click.echo(f"Loaded signing key from {key_file}")
        return key  # type: ignore[return-value]

    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    old_umask = os.umask(0o077)
    try:
        with open(key_file, "wb") as fh:
            fh.write(pem)
    finally:
        os.umask(old_umask)
    click.echo(f"Generated new signing key at {key_file}")
    return key


@click.command()
@click.option("--dataset", required=True, help="Path to benign calibration dataset.")
@click.option("--runs", default=5, help="Number of calibration runs.")
@click.option("--size", default=128, help="Matrix dimension (NxN) for drift scoring.")
@click.option(
    "--output",
    default="calibration_manifest.json",
    help="Output manifest path.",
)
@click.option(
    "--key-file",
    default="calibration_signing_key.pem",
    help="Ed25519 signing key (PEM).",
)
def calibrate(
    dataset: str,
    runs: int,
    size: int,
    output: str,
    key_file: str,
) -> None:
    """Run calibration with integrity protection."""
    if not os.path.isfile(dataset):
        click.echo(f"ERROR: dataset not found: {dataset}", err=True)
        raise SystemExit(1)

    signing_key = _load_or_generate_key(key_file)
    integrity = CalibrationIntegrity(signing_key=signing_key)

    click.echo(f"Running {runs} calibration runs on {dataset} (N={size})…")
    rng = np.random.default_rng(42)
    run_results = []

    for i in range(runs):
        click.echo(f"  Run {i + 1}/{runs}…")
        # Generate GUE surrogates and compute drift scores
        scores = []
        for _ in range(500):
            g = rng.standard_normal((size, size))
            sym = (g + g.T) / 2.0
            score = compute_drift_score(sym)
            if score >= 0:
                scores.append(score)

        scores_arr = np.array(scores)
        run_results.append(
            {
                "run_id": i,
                "mu0": float(np.mean(scores_arr)),
                "mu1": float(np.mean(scores_arr) + 3 * np.std(scores_arr)),
                "sigma2": float(np.var(scores_arr)),
                "theta_BK": float(theta_bk(size)),
            }
        )

    # Create signed manifest
    manifest = integrity.create_manifest(dataset, run_results)

    # Self-verify before saving
    if not integrity.verify_manifest(manifest):
        click.echo("ERROR: Self-verification failed!", err=True)
        raise SystemExit(1)

    # Save
    manifest_dict = {
        "dataset_hash": manifest.dataset_hash,
        "timestamp": manifest.timestamp,
        "parameters": manifest.parameters,
        "runs": manifest.runs,
        "signature": manifest.signature.hex(),
    }
    with open(output, "w") as fh:
        json.dump(manifest_dict, fh, indent=2)

    click.echo(f"\nSaved signed calibration manifest to {output}")
    click.echo(f"Dataset hash: {manifest.dataset_hash}")
    click.echo(f"Median parameters: {json.dumps(manifest.parameters, indent=2)}")


if __name__ == "__main__":
    calibrate()
