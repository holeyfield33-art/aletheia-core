# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Unified Sovereign Runtime — orchestrates the three anchors.

Pipeline:
  1. Pre-execution: ZSP enforcement + token velocity check
  2. Chain signing: Cryptographic anchor (Gate C1)
  3. During execution: Spectral rigidity monitoring (Gate M1)
  4. Post-execution: Full-chain signature + audit commit

This module is designed to be called from the existing
``bridge/fastapi_wrapper.py`` pipeline *after* the tri-agent
evaluation (Scout → Nitpicker → Judge) has completed.

The three anchors are independent fail-closed gates: any single
anchor failure results in an ABORT decision.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from crypto.chain_signer import ChainSigner, ChainSignatureError
from crypto.tpm_interface import TPMAnchor
from economics.circuit_breaker import BreakerState, ResourceCircuitBreaker
from economics.token_velocity import TokenVelocityTracker
from economics.zero_standing_privileges import (
    RequestPrivileges,
    ZSPEnforcer,
)
from monitoring.escalation_probe import temporal_cross_covariance
from monitoring.spectral_rigidity import (
    INCONCLUSIVE,
    compute_drift_score,
    theta_bk,
)
from monitoring.swarm_detector import SwarmDetector, SwarmDetectorConfig

_logger = logging.getLogger("aletheia.unified_audit")


@dataclass(frozen=True)
class SovereignDecision:
    """Result from the Unified Sovereign Runtime."""

    status: str  # "PROCEED", "ABORT", "CIRCUIT_OPEN"
    reason: str = ""
    chain_signature: str = ""
    chain_nonce: str = ""
    drift_score: float = 0.0
    token_budget_remaining: int = 0
    gate_details: dict[str, Any] = field(default_factory=dict)


class UnifiedSovereignRuntime:
    """Orchestrates cryptographic, mathematical, and economic anchors."""

    def __init__(
        self,
        *,
        allowed_resources: set[str] | None = None,
        max_tokens_per_sec: float = 100.0,
        max_hour_budget: int = 10_000,
        max_session_budget: int = 5_000,
        breaker_threshold: int = 5,
        breaker_cooldown: float = 60.0,
        swarm_config: SwarmDetectorConfig | None = None,
    ) -> None:
        self._tpm = TPMAnchor()
        self._signer = ChainSigner(self._tpm)
        self._zsp = ZSPEnforcer(allowed_resources=allowed_resources)
        self._velocity = TokenVelocityTracker(
            max_tokens_per_sec=max_tokens_per_sec,
            max_hour_budget=max_hour_budget,
            max_session_budget=max_session_budget,
        )
        self._breaker = ResourceCircuitBreaker(
            failure_threshold=breaker_threshold,
            cooldown_sec=breaker_cooldown,
        )
        self._prev_activation: np.ndarray | None = None
        self._swarm = SwarmDetector(swarm_config)

    # ------------------------------------------------------------------
    # Pre-execution gate
    # ------------------------------------------------------------------
    def pre_execution_gate(
        self,
        session_id: str,
        request: dict,
        token_estimate: int = 1,
    ) -> SovereignDecision | None:
        """Run pre-execution checks (ZSP + velocity + circuit breaker).

        Returns ``None`` if all gates pass, or a ``SovereignDecision``
        with status="ABORT" if any gate fails.
        """
        # Circuit breaker check
        if not self._breaker.check():
            return SovereignDecision(
                status="CIRCUIT_OPEN",
                reason="ASI-E1: Resource circuit breaker is open",
            )

        # Gate E1: Zero Standing Privileges
        privileges = RequestPrivileges.from_list(request.get("required_resources"))
        zsp_result = self._zsp.enforce(session_id, privileges)
        if not zsp_result.allowed:
            self._breaker.record_failure()
            return SovereignDecision(
                status="ABORT",
                reason=zsp_result.reason,
                gate_details={"gate": "E1_ZSP"},
            )

        # Token velocity check
        vel_result = self._velocity.check_and_consume(token_estimate)
        if not vel_result.allowed:
            self._breaker.record_failure()
            return SovereignDecision(
                status="ABORT",
                reason=f"ASI-E1: {vel_result.reason}",
                gate_details={
                    "gate": "E1_VELOCITY",
                    "hour_total": vel_result.hour_total,
                    "session_total": vel_result.session_total,
                },
            )

        self._breaker.record_success()
        return None

    # ------------------------------------------------------------------
    # During-execution gate (per inference step)
    # ------------------------------------------------------------------
    def gate_m1(
        self,
        activation_matrix: np.ndarray,
        step: int = 0,
    ) -> SovereignDecision | None:
        """Gate M1: spectral rigidity check on an activation snapshot.

        Returns ``None`` if the activation passes, or an ABORT decision
        if manifold drift is detected.
        """
        D = compute_drift_score(activation_matrix)

        if D == INCONCLUSIVE:
            # TMRP k=1 escalation: cross-layer covariance
            if self._prev_activation is not None:
                D = temporal_cross_covariance(self._prev_activation, activation_matrix)
            else:
                D = 0.0  # Cannot escalate on first step

        self._prev_activation = activation_matrix.copy()

        threshold = theta_bk(activation_matrix.shape[0])
        if D > threshold:
            _logger.error(
                "ASI-22: Manifold drift at step %d — D=%.6f > θ_BK=%.6f",
                step,
                D,
                threshold,
            )
            return SovereignDecision(
                status="ABORT",
                reason="ASI-22: Jailbreak or latent evasion detected",
                drift_score=D,
                gate_details={
                    "gate": "M1_SPECTRAL",
                    "step": step,
                    "threshold": threshold,
                },
            )

        return None

    # ------------------------------------------------------------------
    # Post-execution: sign full chain
    # ------------------------------------------------------------------
    def post_execution_sign(
        self,
        request: dict,
        response: dict,
    ) -> SovereignDecision:
        """Gate C1: sign the full request→response chain.

        Returns a PROCEED decision with the chain signature on success,
        or ABORT on confused deputy / signing failure.
        """
        try:
            signed = self._signer.verify_and_sign(request, response)
            return SovereignDecision(
                status="PROCEED",
                chain_signature=signed.get("_chain_signature", ""),
                chain_nonce=signed.get("_chain_nonce", ""),
                gate_details={"gate": "C1_CHAIN", "signer": self._tpm.backend_type},
            )
        except ChainSignatureError as exc:
            _logger.error("Chain signing failed: %s", exc)
            return SovereignDecision(
                status="ABORT",
                reason=str(exc),
                gate_details={"gate": "C1_CHAIN"},
            )

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------
    def execute(
        self,
        request: dict,
        response: dict,
        *,
        session_id: str = "default",
        token_estimate: int = 1,
        activation_snapshots: list[np.ndarray] | None = None,
    ) -> SovereignDecision:
        """Run the full three-anchor pipeline.

        Parameters
        ----------
        request : dict with at least ``action``, ``payload``.
        response : dict — the tri-agent pipeline result.
        session_id : session identifier for ZSP scoping.
        token_estimate : estimated token count for velocity tracking.
        activation_snapshots : optional list of activation matrices
            for spectral rigidity monitoring.

        Returns
        -------
        SovereignDecision with status PROCEED or ABORT.
        """
        # 1. Pre-execution gates
        pre = self.pre_execution_gate(session_id, request, token_estimate)
        if pre is not None:
            return pre

        # 2. Spectral rigidity (if activations provided)
        if activation_snapshots:
            for step, activation in enumerate(activation_snapshots):
                m1 = self.gate_m1(activation, step=step)
                if m1 is not None:
                    return m1

                # Per-step token consumption
                vel = self._velocity.check_and_consume(1)
                if not vel.allowed:
                    self._breaker.open()
                    return SovereignDecision(
                        status="ABORT",
                        reason=f"ASI-E1: {vel.reason}",
                        gate_details={"gate": "E1_VELOCITY", "step": step},
                    )

        # 3. Post-execution: chain signing
        return self.post_execution_sign(request, response)

    # ------------------------------------------------------------------
    # Swarm aggregation
    # ------------------------------------------------------------------
    def aggregate_swarm_window(
        self,
        session_results: list[dict],
    ) -> bool:
        """Aggregate per-session results and run SPRT swarm detection.

        Parameters
        ----------
        session_results : list of dicts, each with at least
            ``drift_score`` (float; −1.0 = INCONCLUSIVE).

        Returns
        -------
        True if a swarm attack is declared (circuit breaker tripped).
        """
        drifts = [
            r["drift_score"] for r in session_results if r.get("drift_score", -1.0) >= 0
        ]
        inconclusive_count = sum(
            1 for r in session_results if r.get("drift_score") == -1.0
        )
        attack, llr = self._swarm.update(
            drifts,
            inconclusive_count,
            len(session_results),
        )
        if attack:
            self._breaker.open()
            _logger.error(
                "Swarm attack declared (LLR=%.4f) — circuit breaker tripped",
                llr,
            )
        return attack

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def breaker_state(self) -> BreakerState:
        return self._breaker.state

    @property
    def session_tokens(self) -> int:
        return self._velocity.session_total

    def reset(self) -> None:
        """Reset all state (test helper)."""
        self._velocity.reset()
        self._breaker.reset()
        self._prev_activation = None
        self._swarm.reset()
