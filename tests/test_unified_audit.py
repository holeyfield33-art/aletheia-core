"""Tests for the Unified Sovereign Runtime."""
from __future__ import annotations

import unittest

import numpy as np

from core.unified_audit import SovereignDecision, UnifiedSovereignRuntime
from economics.circuit_breaker import BreakerState


class TestUnifiedSovereignRuntime(unittest.TestCase):
    """Integration tests for the three-anchor pipeline."""

    def setUp(self) -> None:
        self.runtime = UnifiedSovereignRuntime(
            allowed_resources={"tool:calculator", "tool:search", "max_tokens:500"},
            max_tokens_per_sec=100.0,
            max_hour_budget=10_000,
            max_session_budget=5_000,
            breaker_threshold=3,
            breaker_cooldown=0.01,
        )

    def tearDown(self) -> None:
        self.runtime.reset()

    # ------------------------------------------------------------------
    # Pre-execution gate (ZSP + velocity)
    # ------------------------------------------------------------------
    def test_pre_gate_passes_with_valid_request(self) -> None:
        req = {"required_resources": ["tool:calculator"]}
        result = self.runtime.pre_execution_gate("sess1", req, token_estimate=1)
        self.assertIsNone(result, "Valid request should pass pre-execution gate")

    def test_pre_gate_rejects_no_resources(self) -> None:
        req = {}
        result = self.runtime.pre_execution_gate("sess1", req, token_estimate=1)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "ABORT")
        self.assertIn("ZSP", result.reason)

    def test_pre_gate_rejects_disallowed_resource(self) -> None:
        req = {"required_resources": ["tool:admin_panel"]}
        result = self.runtime.pre_execution_gate("sess1", req, token_estimate=1)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "ABORT")

    def test_pre_gate_velocity_exceeded(self) -> None:
        rt = UnifiedSovereignRuntime(
            max_tokens_per_sec=5, max_session_budget=10000
        )
        req = {"required_resources": ["tool:any"]}
        # Consume all velocity budget
        for _ in range(5):
            result = rt.pre_execution_gate("s", req, token_estimate=1)
            self.assertIsNone(result)
        # Next should fail
        result = rt.pre_execution_gate("s", req, token_estimate=1)
        self.assertIsNotNone(result)
        self.assertIn("velocity", result.reason.lower())

    def test_pre_gate_circuit_breaker_trips(self) -> None:
        """Repeated ZSP violations should trip the circuit breaker."""
        req = {}  # No resources → ZSP violation
        for _ in range(3):
            self.runtime.pre_execution_gate("s", req)
        self.assertEqual(self.runtime.breaker_state, BreakerState.OPEN)
        # Next call should get CIRCUIT_OPEN
        result = self.runtime.pre_execution_gate("s", req)
        self.assertEqual(result.status, "CIRCUIT_OPEN")

    # ------------------------------------------------------------------
    # Gate M1 (spectral rigidity)
    # ------------------------------------------------------------------
    def test_gate_m1_safe_matrix(self) -> None:
        rng = np.random.default_rng(42)
        mat = rng.standard_normal((10, 10))
        mat = (mat + mat.T) / 2
        result = self.runtime.gate_m1(mat, step=0)
        # Safe matrices should pass
        self.assertIsNone(result)

    def test_gate_m1_small_matrix_passes(self) -> None:
        result = self.runtime.gate_m1(np.eye(3), step=0)
        self.assertIsNone(result, "Small matrices should be skipped")

    def test_gate_m1_tracks_previous(self) -> None:
        rng = np.random.default_rng(42)
        mat1 = rng.standard_normal((10, 10))
        mat2 = rng.standard_normal((10, 10))
        self.runtime.gate_m1(mat1, step=0)
        result = self.runtime.gate_m1(mat2, step=1)
        # Should not be None if drift is high, or None if safe
        self.assertTrue(result is None or result.status == "ABORT")

    # ------------------------------------------------------------------
    # Post-execution chain signing
    # ------------------------------------------------------------------
    def test_post_execution_sign_basic(self) -> None:
        req = {"action": "Read_Report", "payload": "test"}
        resp = {"decision": "PROCEED"}
        result = self.runtime.post_execution_sign(req, resp)
        self.assertEqual(result.status, "PROCEED")
        self.assertGreater(len(result.chain_signature), 0)
        self.assertGreater(len(result.chain_nonce), 0)

    def test_post_execution_confused_deputy(self) -> None:
        req = {
            "tool": "file_writer",
            "intent": {"specified_tool": "calculator"},
        }
        resp = {"decision": "PROCEED"}
        result = self.runtime.post_execution_sign(req, resp)
        self.assertEqual(result.status, "ABORT")
        self.assertIn("ASI-04", result.reason)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def test_full_pipeline_proceed(self) -> None:
        req = {
            "action": "Read_Report",
            "payload": "quarterly summary",
            "required_resources": ["tool:calculator"],
        }
        resp = {"decision": "PROCEED"}
        result = self.runtime.execute(
            req, resp, session_id="test", token_estimate=1
        )
        self.assertEqual(result.status, "PROCEED")
        self.assertGreater(len(result.chain_signature), 0)

    def test_full_pipeline_with_activations(self) -> None:
        rng = np.random.default_rng(42)
        activations = [
            (rng.standard_normal((10, 10)) + rng.standard_normal((10, 10)).T) / 2
            for _ in range(3)
        ]
        req = {
            "action": "Read_Report",
            "payload": "test",
            "required_resources": ["tool:search"],
        }
        resp = {"decision": "PROCEED"}
        result = self.runtime.execute(
            req, resp,
            session_id="test",
            token_estimate=1,
            activation_snapshots=activations,
        )
        # Should proceed (random symmetric matrices should be safe)
        self.assertEqual(result.status, "PROCEED")

    def test_full_pipeline_zsp_abort(self) -> None:
        req = {"action": "Transfer_Funds", "payload": "wire $100k"}
        resp = {"decision": "DENIED"}
        result = self.runtime.execute(req, resp, session_id="test")
        self.assertEqual(result.status, "ABORT")
        self.assertIn("ZSP", result.reason)

    def test_session_token_tracking(self) -> None:
        req = {"required_resources": ["tool:calculator"]}
        self.runtime.pre_execution_gate("s", req, token_estimate=10)
        self.assertEqual(self.runtime.session_tokens, 10)
        self.runtime.pre_execution_gate("s", req, token_estimate=5)
        self.assertEqual(self.runtime.session_tokens, 15)


class TestSovereignDecision(unittest.TestCase):
    def test_default_values(self) -> None:
        d = SovereignDecision(status="PROCEED")
        self.assertEqual(d.status, "PROCEED")
        self.assertEqual(d.reason, "")
        self.assertEqual(d.chain_signature, "")
        self.assertEqual(d.drift_score, 0.0)
        self.assertEqual(d.gate_details, {})


if __name__ == "__main__":
    unittest.main()
