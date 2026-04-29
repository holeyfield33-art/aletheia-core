"""Swarm detection using SPRT on sliding-window trimmed-mean drift,
gated by an INCONCLUSIVE-rate floor.

The detector watches aggregated drift scores across sessions.  When the
Sequential Probability Ratio Test (SPRT) log-likelihood crosses the
upper threshold *and* the INCONCLUSIVE rate stays above ``r_min``, a
swarm attack is declared and the caller can trip the circuit breaker.

Calibrate ``mu0``, ``mu1``, ``sigma2`` empirically using
``scripts/calibrate_bk_threshold.py`` or a production replay.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

_logger = logging.getLogger("aletheia.monitoring.swarm_detector")


@dataclass
class SwarmDetectorConfig:
    window_size: int = 60  # number of windows to track
    trim_fraction: float = 0.05  # trim top/bottom 5%
    r_min: float = 0.05  # minimum INCONCLUSIVE rate floor
    alpha: float = 1e-4  # false-positive target
    beta: float = 1e-2  # false-negative target
    mu0: float = 0.1  # benign mean drift (calibrated)
    mu1: float = 0.4  # attack mean drift (calibrated)
    sigma2: float = 0.04  # variance (calibrated)


class SwarmDetector:
    """SPRT-based swarm attack detector with INCONCLUSIVE-rate gating."""

    def __init__(self, config: SwarmDetectorConfig | None = None) -> None:
        self.config = config or SwarmDetectorConfig()
        self.drift_window: deque[float] = deque(maxlen=self.config.window_size)
        self.inconclusive_window: deque[float] = deque(maxlen=self.config.window_size)
        self.log_likelihood_ratio: float = 0.0
        self.attack_declared: bool = False

    def update(
        self,
        per_session_drifts: List[float],
        inconclusive_count: int,
        total_sessions: int,
    ) -> Tuple[bool, float]:
        """Ingest one time-window of drift data and run SPRT.

        Parameters
        ----------
        per_session_drifts : list of per-session drift scores (≥ 0).
        inconclusive_count : sessions that returned ``INCONCLUSIVE``.
        total_sessions : total sessions in this window.

        Returns
        -------
        (attack_detected, current_log_likelihood_ratio)
        """
        if len(per_session_drifts) == 0:
            return False, self.log_likelihood_ratio

        trimmed = self._trimmed_mean(per_session_drifts)
        self.drift_window.append(trimmed)

        inconclusive_rate = (
            inconclusive_count / total_sessions if total_sessions > 0 else 0.0
        )
        self.inconclusive_window.append(inconclusive_rate)

        # Gate: need at least half a window of history
        if len(self.inconclusive_window) < self.config.window_size // 2:
            return False, self.log_likelihood_ratio

        # Gate: INCONCLUSIVE rate floor must be met across recent windows
        recent_rates = list(self.inconclusive_window)[-10:]
        if not all(r >= self.config.r_min for r in recent_rates):
            return False, self.log_likelihood_ratio

        # Update SPRT with recent drift observations
        recent_drifts = list(self.drift_window)[-5:]
        for d in recent_drifts:
            self.log_likelihood_ratio += self._log_likelihood_increment(d)

        # Upper threshold → attack
        upper = math.log((1 - self.config.beta) / self.config.alpha)
        if self.log_likelihood_ratio >= upper:
            self.attack_declared = True
            _logger.error(
                "SPRT swarm attack declared — LLR=%.4f ≥ threshold=%.4f",
                self.log_likelihood_ratio,
                upper,
            )
            return True, self.log_likelihood_ratio

        # Lower threshold → strong evidence of no attack; reset accumulator
        if self.log_likelihood_ratio < -upper:
            self.log_likelihood_ratio = 0.0

        return False, self.log_likelihood_ratio

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _trimmed_mean(self, values: List[float]) -> float:
        """Trimmed mean: remove top/bottom ``trim_fraction``."""
        if len(values) == 0:
            return 0.0
        sorted_vals = np.sort(values)
        trim_n = int(len(sorted_vals) * self.config.trim_fraction)
        if trim_n * 2 >= len(sorted_vals):
            return float(np.mean(sorted_vals))
        trimmed = sorted_vals[trim_n : len(sorted_vals) - trim_n]
        return float(np.mean(trimmed))

    def _log_likelihood_increment(self, drift: float) -> float:
        """Log-likelihood ratio increment under Gaussian assumption.

        ``ln(f₁/f₀) = (μ₁ − μ₀)/σ² · (x − (μ₀ + μ₁)/2)``
        """
        mu0 = self.config.mu0
        mu1 = self.config.mu1
        sigma2 = self.config.sigma2
        if sigma2 <= 0:
            return 0.0
        return ((mu1 - mu0) / sigma2) * (drift - (mu0 + mu1) / 2)

    def reset(self) -> None:
        """Reset detector state (after attack handled or false alarm)."""
        self.drift_window.clear()
        self.inconclusive_window.clear()
        self.log_likelihood_ratio = 0.0
        self.attack_declared = False
