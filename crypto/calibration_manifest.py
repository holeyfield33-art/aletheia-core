"""Signed calibration manifests with multi-run consensus and outlier rejection.

Ensures that calibration parameters (μ₀, μ₁, σ², θ_BK) are:
1. Derived from a known, hash-pinned dataset.
2. Computed across multiple independent runs with median consensus.
3. Protected against poisoned runs via outlier rejection.
4. Signed with Ed25519 so downstream consumers can verify provenance.

The signing key should be the same Ed25519 key used for policy
manifest signing (``manifest/signing.py``) or a dedicated
calibration-only key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_logger = logging.getLogger("aletheia.crypto.calibration_manifest")

# Keys that carry numeric calibration values (used for median / outlier detection).
_NUMERIC_PARAM_KEYS = frozenset({"mu0", "mu1", "sigma2", "theta_BK"})


@dataclass
class CalibrationManifest:
    """Immutable calibration result with provenance chain."""

    dataset_hash: str  # SHA3-256 of calibration dataset
    timestamp: int
    parameters: Dict[str, float]  # mu0, mu1, sigma2, theta_BK, …
    runs: List[Dict[str, Any]]  # individual run results
    signature: bytes = b""


class CalibrationIntegrity:
    """Create and verify Ed25519-signed calibration manifests."""

    def __init__(
        self,
        signing_key: Ed25519PrivateKey | None = None,
        verifying_key: Ed25519PublicKey | None = None,
    ) -> None:
        if signing_key is None and verifying_key is None:
            raise ValueError(
                "At least one of signing_key or verifying_key must be provided"
            )
        self._signing_key = signing_key
        self._verifying_key = (
            verifying_key if verifying_key is not None else signing_key.public_key()  # type: ignore[union-attr]
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_manifest(
        self,
        dataset_path: str,
        run_results: List[Dict[str, Any]],
        *,
        outlier_threshold: float = 2.0,
    ) -> CalibrationManifest:
        """Create a signed manifest from calibration runs.

        Raises ``ValueError`` if more than half of the runs are outliers
        (possible poisoning).
        """
        if self._signing_key is None:
            raise RuntimeError("Cannot create manifest without a signing key")

        dataset_hash = self._hash_dataset(dataset_path)

        filtered_runs, outliers = self._reject_outliers(
            run_results,
            threshold=outlier_threshold,
        )
        if len(filtered_runs) < len(run_results) * 0.5:
            raise ValueError(
                f"Too many outlier runs ({len(outliers)}/{len(run_results)}) "
                "— calibration may be poisoned"
            )
        if outliers:
            _logger.warning(
                "Rejected %d outlier run(s) from calibration",
                len(outliers),
            )

        median_params = self._median_across_runs(filtered_runs)

        manifest = CalibrationManifest(
            dataset_hash=dataset_hash,
            timestamp=int(time.time()),
            parameters=median_params,
            runs=filtered_runs,
        )

        manifest_bytes = _serialize(manifest)
        manifest.signature = self._signing_key.sign(manifest_bytes)
        return manifest

    def verify_manifest(self, manifest: CalibrationManifest) -> bool:
        """Verify the Ed25519 signature over the manifest payload."""
        sig = manifest.signature
        manifest_bytes = _serialize(
            CalibrationManifest(
                dataset_hash=manifest.dataset_hash,
                timestamp=manifest.timestamp,
                parameters=manifest.parameters,
                runs=manifest.runs,
                signature=b"",
            )
        )
        try:
            self._verifying_key.verify(sig, manifest_bytes)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_dataset(path: str) -> str:
        """SHA3-256 of the calibration dataset file."""
        hasher = hashlib.sha3_256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _median_across_runs(runs: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute the median of each numeric parameter across runs."""
        if not runs:
            return {}
        medians: Dict[str, float] = {}
        for key in _NUMERIC_PARAM_KEYS:
            values = sorted(
                r[key] for r in runs if key in r and isinstance(r[key], (int, float))
            )
            if values:
                mid = len(values) // 2
                medians[key] = float(values[mid])
        return medians

    @staticmethod
    def _reject_outliers(
        runs: List[Dict[str, Any]],
        threshold: float = 2.0,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Reject runs with any numeric parameter beyond *threshold* × σ from the median."""
        if len(runs) < 3:
            return list(runs), []

        filtered: List[Dict[str, Any]] = []
        outliers: List[Dict[str, Any]] = []

        for run in runs:
            is_outlier = False
            for key in _NUMERIC_PARAM_KEYS:
                if key not in run or not isinstance(run[key], (int, float)):
                    continue
                values = [
                    r[key]
                    for r in runs
                    if key in r and isinstance(r[key], (int, float))
                ]
                if len(values) < 3:
                    continue
                median = float(sorted(values)[len(values) // 2])
                std = float(np.std(values))
                if std > 0 and abs(run[key] - median) > threshold * std:
                    is_outlier = True
                    break
            if is_outlier:
                outliers.append(run)
            else:
                filtered.append(run)

        return filtered, outliers


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _serialize(manifest: CalibrationManifest) -> bytes:
    """Deterministic JSON serialisation of the unsigned manifest fields."""
    data = {
        "dataset_hash": manifest.dataset_hash,
        "timestamp": manifest.timestamp,
        "parameters": manifest.parameters,
        "runs": manifest.runs,
    }
    return json.dumps(data, sort_keys=True, default=str).encode("utf-8")
