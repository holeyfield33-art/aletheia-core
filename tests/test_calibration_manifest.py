"""Tests for the calibration integrity protocol."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from crypto.calibration_manifest import (
    CalibrationIntegrity,
    CalibrationManifest,
)


def _sample_runs(n: int = 5, seed: int = 42) -> list[dict]:
    """Generate realistic calibration run results."""
    rng = np.random.default_rng(seed)
    return [
        {
            "run_id": i,
            "mu0": float(rng.normal(0.10, 0.005)),
            "mu1": float(rng.normal(0.40, 0.01)),
            "sigma2": float(rng.normal(0.04, 0.002)),
            "theta_BK": 1.74,
        }
        for i in range(n)
    ]


def _make_dataset_file(content: bytes = b"test calibration data") -> str:
    """Create a temp file that acts as a calibration dataset."""
    fd, path = tempfile.mkstemp(suffix=".dat")
    os.write(fd, content)
    os.close(fd)
    return path


class TestCalibrationManifestCreation(unittest.TestCase):
    def setUp(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.integrity = CalibrationIntegrity(signing_key=self.key)
        self.dataset = _make_dataset_file()

    def tearDown(self) -> None:
        os.unlink(self.dataset)

    def test_create_and_verify(self) -> None:
        runs = _sample_runs(5)
        manifest = self.integrity.create_manifest(self.dataset, runs)
        self.assertTrue(self.integrity.verify_manifest(manifest))
        self.assertGreater(len(manifest.signature), 0)
        self.assertIn("mu0", manifest.parameters)
        self.assertIn("mu1", manifest.parameters)

    def test_dataset_hash_deterministic(self) -> None:
        runs = _sample_runs(3)
        m1 = self.integrity.create_manifest(self.dataset, runs)
        m2 = self.integrity.create_manifest(self.dataset, runs)
        self.assertEqual(m1.dataset_hash, m2.dataset_hash)

    def test_different_dataset_different_hash(self) -> None:
        other = _make_dataset_file(b"different data")
        try:
            runs = _sample_runs(3)
            m1 = self.integrity.create_manifest(self.dataset, runs)
            m2 = self.integrity.create_manifest(other, runs)
            self.assertNotEqual(m1.dataset_hash, m2.dataset_hash)
        finally:
            os.unlink(other)

    def test_timestamp_present(self) -> None:
        runs = _sample_runs(3)
        manifest = self.integrity.create_manifest(self.dataset, runs)
        self.assertGreater(manifest.timestamp, 0)

    def test_runs_preserved(self) -> None:
        # Use constant data so no outliers are detected
        runs = [
            {"run_id": i, "mu0": 0.10, "mu1": 0.40, "sigma2": 0.04, "theta_BK": 1.74}
            for i in range(5)
        ]
        manifest = self.integrity.create_manifest(self.dataset, runs)
        self.assertEqual(len(manifest.runs), 5)


class TestSignatureVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.integrity = CalibrationIntegrity(signing_key=self.key)
        self.dataset = _make_dataset_file()

    def tearDown(self) -> None:
        os.unlink(self.dataset)

    def test_tampered_parameters_fail(self) -> None:
        manifest = self.integrity.create_manifest(self.dataset, _sample_runs(5))
        manifest.parameters["mu0"] = 999.0
        self.assertFalse(self.integrity.verify_manifest(manifest))

    def test_tampered_dataset_hash_fail(self) -> None:
        manifest = self.integrity.create_manifest(self.dataset, _sample_runs(5))
        manifest = CalibrationManifest(
            dataset_hash="0" * 64,
            timestamp=manifest.timestamp,
            parameters=manifest.parameters,
            runs=manifest.runs,
            signature=manifest.signature,
        )
        self.assertFalse(self.integrity.verify_manifest(manifest))

    def test_wrong_key_fails(self) -> None:
        manifest = self.integrity.create_manifest(self.dataset, _sample_runs(5))
        other_key = Ed25519PrivateKey.generate()
        other_integrity = CalibrationIntegrity(signing_key=other_key)
        self.assertFalse(other_integrity.verify_manifest(manifest))

    def test_empty_signature_fails(self) -> None:
        manifest = self.integrity.create_manifest(self.dataset, _sample_runs(5))
        manifest = CalibrationManifest(
            dataset_hash=manifest.dataset_hash,
            timestamp=manifest.timestamp,
            parameters=manifest.parameters,
            runs=manifest.runs,
            signature=b"",
        )
        self.assertFalse(self.integrity.verify_manifest(manifest))

    def test_verify_only_mode(self) -> None:
        """CalibrationIntegrity with only a public key can verify but not sign."""
        manifest = self.integrity.create_manifest(self.dataset, _sample_runs(5))
        verifier = CalibrationIntegrity(verifying_key=self.key.public_key())
        self.assertTrue(verifier.verify_manifest(manifest))
        with self.assertRaises(RuntimeError):
            verifier.create_manifest(self.dataset, _sample_runs(3))


class TestMedianAcrossRuns(unittest.TestCase):
    def test_median_computation(self) -> None:
        runs = [
            {"mu0": 0.08, "mu1": 0.38, "sigma2": 0.03, "theta_BK": 1.7},
            {"mu0": 0.10, "mu1": 0.40, "sigma2": 0.04, "theta_BK": 1.7},
            {"mu0": 0.12, "mu1": 0.42, "sigma2": 0.05, "theta_BK": 1.7},
        ]
        medians = CalibrationIntegrity._median_across_runs(runs)
        self.assertAlmostEqual(medians["mu0"], 0.10)
        self.assertAlmostEqual(medians["mu1"], 0.40)
        self.assertAlmostEqual(medians["sigma2"], 0.04)

    def test_empty_runs(self) -> None:
        self.assertEqual(CalibrationIntegrity._median_across_runs([]), {})

    def test_ignores_non_numeric_keys(self) -> None:
        runs = [
            {"run_id": 0, "mu0": 0.1, "mu1": 0.4, "sigma2": 0.04, "theta_BK": 1.7},
            {"run_id": 1, "mu0": 0.1, "mu1": 0.4, "sigma2": 0.04, "theta_BK": 1.7},
        ]
        medians = CalibrationIntegrity._median_across_runs(runs)
        self.assertNotIn("run_id", medians)


class TestOutlierRejection(unittest.TestCase):
    def test_no_outliers(self) -> None:
        # Use tight, constant data to guarantee zero outliers
        runs = [
            {"mu0": 0.10, "mu1": 0.40, "sigma2": 0.04, "theta_BK": 1.74}
            for _ in range(5)
        ]
        filtered, outliers = CalibrationIntegrity._reject_outliers(runs)
        self.assertEqual(len(outliers), 0)
        self.assertEqual(len(filtered), 5)

    def test_detects_outlier(self) -> None:
        runs = _sample_runs(10)
        # Inject a wild outlier
        runs.append(
            {
                "run_id": 99,
                "mu0": 50.0,  # way out of range
                "mu1": 0.4,
                "sigma2": 0.04,
                "theta_BK": 1.7,
            }
        )
        filtered, outliers = CalibrationIntegrity._reject_outliers(runs)
        self.assertGreater(len(outliers), 0)
        outlier_ids = [o["run_id"] for o in outliers]
        self.assertIn(99, outlier_ids)

    def test_too_few_runs_no_rejection(self) -> None:
        runs = _sample_runs(2)
        filtered, outliers = CalibrationIntegrity._reject_outliers(runs)
        self.assertEqual(len(outliers), 0)
        self.assertEqual(len(filtered), 2)

    def test_majority_outliers_raises(self) -> None:
        """create_manifest should raise if > 50% of runs are outliers."""
        key = Ed25519PrivateKey.generate()
        integrity = CalibrationIntegrity(signing_key=key)
        dataset = _make_dataset_file()
        try:
            runs = _sample_runs(10)
            # Patch _reject_outliers to simulate majority poisoning
            fake_filtered = runs[:3]
            fake_outliers = runs[3:]
            with patch.object(
                CalibrationIntegrity,
                "_reject_outliers",
                return_value=(fake_filtered, fake_outliers),
            ):
                with self.assertRaises(ValueError) as ctx:
                    integrity.create_manifest(dataset, runs)
                self.assertIn("poisoned", str(ctx.exception))
        finally:
            os.unlink(dataset)

    def test_custom_threshold(self) -> None:
        runs = _sample_runs(10)
        # Very tight threshold should reject more
        _, outliers_tight = CalibrationIntegrity._reject_outliers(runs, threshold=0.5)
        _, outliers_loose = CalibrationIntegrity._reject_outliers(runs, threshold=5.0)
        self.assertGreaterEqual(len(outliers_tight), len(outliers_loose))


class TestConstructorValidation(unittest.TestCase):
    def test_no_keys_raises(self) -> None:
        with self.assertRaises(ValueError):
            CalibrationIntegrity()


if __name__ == "__main__":
    unittest.main()
