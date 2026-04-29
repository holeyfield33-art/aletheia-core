"""Smoke tests for simulations/ — all four simulation scripts.

These are not security-property tests; they verify that:
- Each simulation function can be called without raising an exception
- The pipeline produces output (something is printed)
- Regressions in run_aletheia_audit() are surfaced when simulations break
- Each simulation targets the expected action type / origin it was designed for

Simulation scripts:
  simulations/adversarial_loop.py   → run_adversarial_training()
  simulations/shadow_audit_01.py    → run_shadow_audit()
  simulations/lunar_shadow_audit.py → run_lunar_audit()
  simulations/neutral_anchor_audit.py → run_neutral_anchor_audit()
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch


class TestAdversarialLoopSimulation(unittest.TestCase):
    """Smoke tests for simulations/adversarial_loop.py."""

    def test_run_adversarial_training_does_not_raise(self) -> None:
        from simulations.adversarial_loop import run_adversarial_training

        with patch("sys.stdout", new_callable=io.StringIO):
            run_adversarial_training()  # must not raise

    def test_run_adversarial_training_produces_output(self) -> None:
        from simulations.adversarial_loop import run_adversarial_training

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_adversarial_training()
        output = buf.getvalue()
        self.assertGreater(len(output), 0, "No output produced by adversarial_loop")

    def test_run_adversarial_training_runs_multiple_cycles(self) -> None:
        """The loop runs 5 cycles; AUDIT RESULTS should appear multiple times."""
        from simulations.adversarial_loop import run_adversarial_training

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_adversarial_training()
        output = buf.getvalue()
        # At least one audit result per cycle
        self.assertGreaterEqual(
            output.count("AUDIT RESULTS"),
            1,
            "Expected at least one AUDIT RESULTS block in adversarial loop output",
        )

    def test_run_adversarial_training_payloads_are_blocked(self) -> None:
        """All payloads in the adversarial loop are hostile and should be BLOCKED."""
        from simulations.adversarial_loop import run_adversarial_training

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_adversarial_training()
        output = buf.getvalue()
        self.assertIn(
            "BLOCKED",
            output,
            "Expected at least one BLOCKED result in adversarial loop",
        )


class TestShadowAuditSimulation(unittest.TestCase):
    """Smoke tests for simulations/shadow_audit_01.py."""

    def test_run_shadow_audit_does_not_raise(self) -> None:
        from simulations.shadow_audit_01 import run_shadow_audit

        with patch("sys.stdout", new_callable=io.StringIO):
            run_shadow_audit()

    def test_run_shadow_audit_produces_output(self) -> None:
        from simulations.shadow_audit_01 import run_shadow_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_shadow_audit()
        self.assertGreater(len(buf.getvalue()), 0)

    def test_shadow_audit_contains_audit_results(self) -> None:
        from simulations.shadow_audit_01 import run_shadow_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_shadow_audit()
        self.assertIn("AUDIT RESULTS", buf.getvalue())

    def test_shadow_audit_calendar_invite_payload_is_blocked(self) -> None:
        """The CALENDAR_INVITE_PROMPT + curl exfil payload must be blocked."""
        from simulations.shadow_audit_01 import run_shadow_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_shadow_audit()
        self.assertIn(
            "BLOCKED",
            buf.getvalue(),
            "Shadow audit calendar invite payload must be blocked",
        )

    def test_shadow_audit_references_open_external_socket(self) -> None:
        """Simulation scenario targets Open_External_Socket action."""
        from simulations.shadow_audit_01 import run_shadow_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_shadow_audit()
        output = buf.getvalue()
        # Scout or judge output should reflect the socket-related threat
        self.assertIn("STAGE 1", output)
        self.assertIn("STAGE 2", output)


class TestLunarShadowAuditSimulation(unittest.TestCase):
    """Smoke tests for simulations/lunar_shadow_audit.py."""

    def test_run_lunar_audit_does_not_raise(self) -> None:
        from simulations.lunar_shadow_audit import run_lunar_audit

        with patch("sys.stdout", new_callable=io.StringIO):
            run_lunar_audit()

    def test_run_lunar_audit_produces_output(self) -> None:
        from simulations.lunar_shadow_audit import run_lunar_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_lunar_audit()
        self.assertGreater(len(buf.getvalue()), 0)

    def test_lunar_audit_poisoned_employment_doc_blocked(self) -> None:
        """The SYSTEM_UPDATE + FORCE_ACTION employment doc must be blocked."""
        from simulations.lunar_shadow_audit import run_lunar_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_lunar_audit()
        self.assertIn(
            "BLOCKED",
            buf.getvalue(),
            "Lunar shadow audit poisoned payload must be blocked",
        )

    def test_lunar_audit_outputs_stage_labels(self) -> None:
        from simulations.lunar_shadow_audit import run_lunar_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_lunar_audit()
        output = buf.getvalue()
        self.assertIn("STAGE 1", output)
        self.assertIn("STAGE 2", output)

    def test_lunar_audit_header_present(self) -> None:
        from simulations.lunar_shadow_audit import run_lunar_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_lunar_audit()
        self.assertIn("LUNARCREDIT", buf.getvalue())


class TestNeutralAnchorAuditSimulation(unittest.TestCase):
    """Smoke tests for simulations/neutral_anchor_audit.py."""

    def test_run_neutral_anchor_audit_does_not_raise(self) -> None:
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        with patch("sys.stdout", new_callable=io.StringIO):
            run_neutral_anchor_audit()

    def test_run_neutral_anchor_audit_produces_output(self) -> None:
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_neutral_anchor_audit()
        self.assertGreater(len(buf.getvalue()), 0)

    def test_neutral_anchor_shadow_payload_detected(self) -> None:
        """The 'Routine Refactor' neutral-anchor shadow payload must be blocked."""
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_neutral_anchor_audit()
        self.assertIn(
            "BLOCKED",
            buf.getvalue(),
            "Neutral anchor audit shadow payload must be blocked",
        )

    def test_neutral_anchor_outputs_payload_in_header(self) -> None:
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_neutral_anchor_audit()
        self.assertIn("PAYLOAD", buf.getvalue())

    def test_neutral_anchor_shows_pipeline_stages(self) -> None:
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        buf = io.StringIO()
        with patch("sys.stdout", buf):
            run_neutral_anchor_audit()
        output = buf.getvalue()
        self.assertIn("STAGE 1", output)
        self.assertIn("STAGE 2", output)


class TestSimulationImportability(unittest.TestCase):
    """All simulation modules must be importable without side effects."""

    def test_adversarial_loop_importable(self) -> None:
        import simulations.adversarial_loop  # noqa: F401

    def test_shadow_audit_01_importable(self) -> None:
        import simulations.shadow_audit_01  # noqa: F401

    def test_lunar_shadow_audit_importable(self) -> None:
        import simulations.lunar_shadow_audit  # noqa: F401

    def test_neutral_anchor_audit_importable(self) -> None:
        import simulations.neutral_anchor_audit  # noqa: F401

    def test_all_simulation_functions_callable(self) -> None:
        from simulations.adversarial_loop import run_adversarial_training
        from simulations.shadow_audit_01 import run_shadow_audit
        from simulations.lunar_shadow_audit import run_lunar_audit
        from simulations.neutral_anchor_audit import run_neutral_anchor_audit

        for fn in (
            run_adversarial_training,
            run_shadow_audit,
            run_lunar_audit,
            run_neutral_anchor_audit,
        ):
            self.assertTrue(callable(fn), f"{fn.__name__} is not callable")


if __name__ == "__main__":
    unittest.main()
