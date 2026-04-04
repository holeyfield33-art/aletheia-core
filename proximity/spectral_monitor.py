"""Aletheia Core — Spectral Monitor Module.

Layer 1: READ-ONLY observer. Calls Geometric Brain MCP to monitor spectral health.
Detects degradation via r_ratio trending below threshold.
"""
from __future__ import annotations
import asyncio
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx


# Configuration (all overridable via env)
GEOMETRIC_BRAIN_URL = os.getenv("GEOMETRIC_BRAIN_URL", "https://geometric-brain-mcp.onrender.com")
POLL_INTERVAL_SECONDS = int(os.getenv("SPECTRAL_POLL_INTERVAL", "30"))
DEGRADATION_THRESHOLD = float(os.getenv("SPECTRAL_DEGRADATION_THRESHOLD", "0.50"))
DEGRADATION_CONSECUTIVE = int(os.getenv("SPECTRAL_DEGRADATION_CONSECUTIVE", "3"))
HISTORY_BUFFER_SIZE = 100

# Spectral constants
GUE_TARGET = 0.603
POISSON_BASELINE = 0.386


@dataclass
class SpectralHealth:
    """Spectral health reading snapshot."""
    r_ratio: float
    spectral_gap: float
    coherence_index: float
    timestamp: datetime
    session_id: str
    raw_response: dict | None = None


class SpectralMonitor:
    """Layer 1: Spectral health monitor."""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        """Initialize spectral monitor.
        
        Args:
            http_client: Optional httpx.AsyncClient for testing. If None, will be created.
        """
        self._client = http_client
        self._own_client = http_client is None
        self._running = False
        self._session_id = ""
        self._current_health: SpectralHealth | None = None
        self._history: deque[SpectralHealth] = deque(maxlen=HISTORY_BUFFER_SIZE)
        self._degradation_streak = 0
        self._background_task: asyncio.Task | None = None

    async def start(self, session_id: str) -> None:
        """Start monitoring spectral health.
        
        Args:
            session_id: Session identifier for tracking.
        """
        if self._running:
            return

        self._session_id = session_id
        self._running = True

        if self._own_client:
            self._client = httpx.AsyncClient(timeout=30.0)

        self._background_task = asyncio.create_task(self._background_poll())

    async def stop(self) -> None:
        """Stop monitoring. Never raises."""
        self._running = False

        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        if self._own_client and self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    async def get_current_health(self) -> SpectralHealth | None:
        """Get current spectral health reading."""
        return self._current_health

    async def is_degraded(self) -> bool:
        """Check if spectral health is degraded."""
        return self._degradation_streak >= DEGRADATION_CONSECUTIVE

    async def get_history(self, n: int = 100) -> list[SpectralHealth]:
        """Get recent spectral history (most recent first)."""
        return list(reversed(self._history))[:n]

    async def poll_once(self) -> SpectralHealth | None:
        """Poll Geometric Brain once. For tests and manual use."""
        if not self._client:
            return None

        try:
            response = await self._client.get(
                f"{GEOMETRIC_BRAIN_URL}/spectral",
                params={"session_id": self._session_id},
            )
            response.raise_for_status()
            data = response.json()

            r_ratio = float(data.get("r_ratio", 0.0))
            spectral_gap = float(data.get("spectral_gap", 0.0))

            health = SpectralHealth(
                r_ratio=r_ratio,
                spectral_gap=spectral_gap,
                coherence_index=self._compute_coherence_index(r_ratio, spectral_gap),
                timestamp=datetime.now(timezone.utc),
                session_id=self._session_id,
                raw_response=data,
            )

            self._current_health = health
            self._history.append(health)

            # Update degradation streak
            if r_ratio < DEGRADATION_THRESHOLD:
                self._degradation_streak += 1
            else:
                self._degradation_streak = 0

            return health

        except (httpx.HTTPError, httpx.ConnectError, ValueError, KeyError):
            # Log warning would happen in real implementation
            return None

    async def _background_poll(self) -> None:
        """Background polling loop."""
        while self._running:
            try:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                if self._running:
                    await self.poll_once()
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue on error
                pass

    @staticmethod
    def _compute_coherence_index(
        r_ratio: float,
        spectral_gap: float,
        baseline_gap: float = 1.0,
    ) -> float:
        """Compute coherence index.
        
        CI = 0.6 × normalized_rigidity + 0.4 × spectral_gap/baseline
        """
        # Normalize rigidity to [0, 1]
        normalized_rigidity = max(
            0.0,
            min(
                1.0,
                (r_ratio - POISSON_BASELINE) / (GUE_TARGET - POISSON_BASELINE),
            ),
        )

        # Normalize gap ratio
        gap_ratio = (
            max(0.0, min(1.0, spectral_gap / baseline_gap))
            if baseline_gap > 0
            else 0.0
        )

        ci = 0.6 * normalized_rigidity + 0.4 * gap_ratio
        return round(ci, 4)
