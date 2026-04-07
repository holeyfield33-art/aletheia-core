"""Aletheia Core — Identity Anchor Module.

Layer 2: Append-only hash chain for decision logging and constitutional consistency.
Integrates with Mneme MCP (best-effort).
"""
from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx

from .spectral_monitor import SpectralHealth


# Configuration
MNEME_URL = os.getenv("MNEME_URL", "http://localhost:8000")
MNEME_API_KEY = os.getenv("MNEME_API_KEY", "")


@dataclass
class DecisionReceipt:
    """Record of a decision made by the relay."""
    action: str
    reasoning: str
    spectral_state: SpectralHealth
    timestamp: datetime
    helios_hash: str = ""
    session_id: str = ""
    request_id: str = ""
    policy_version: str = "UNKNOWN"
    manifest_hash: str = ""
    fallback_state: str = "normal"
    decision_token: str = ""
    approved: bool = True
    policy_violations: list[str] = field(default_factory=list)


@dataclass
class ConstitutionalInvariant:
    """A constitutional principle or boundary."""
    id: str
    statement: str
    category: str  # "value" | "boundary" | "red_line"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Constitution:
    """The constitutional framework."""
    invariants: list[ConstitutionalInvariant]
    version: str
    helios_hash: str


def _helios_hash(content: str, prev_hash: str = "") -> str:
    """Compute chained hash using SHA-256.
    
    Args:
        content: Canonical JSON of the content
        prev_hash: Hash of previous entry in chain
        
    Returns:
        64-character hex digest
    """
    combined = json.dumps(
        {"content": content, "prev": prev_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class IdentityAnchor:
    """Layer 2: Identity anchor for decision logging and constitutional consistency."""

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        """Initialize identity anchor.
        
        Args:
            http_client: Optional httpx.AsyncClient for testing.
        """
        self._client = http_client
        self._own_client = http_client is None
        self._decisions: list[DecisionReceipt] = []
        self._chain_hashes: list[str] = []
        self._seen_tokens: set[str] = set()
        _raw = os.getenv("ALETHEIA_ANCHOR_STATE_PATH", "")
        self._state_path: Path | None = Path(_raw) if _raw else None
        self._constitution: Constitution | None = None
        self._load_state()

    def _load_state(self) -> None:
        if not self._state_path:
            return
        try:
            if not self._state_path.exists():
                return
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            self._chain_hashes = list(data.get("chain_hashes", []))
            self._seen_tokens = set(data.get("seen_tokens", []))
        except Exception:
            # Fail closed during replay checks only; state loading remains best-effort.
            self._chain_hashes = []
            self._seen_tokens = set()

    def _persist_state(self) -> None:
        if not self._state_path:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(
                {
                    "chain_hashes": self._chain_hashes,
                    "seen_tokens": sorted(self._seen_tokens),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    async def open(self) -> None:
        """Open anchor session."""
        if self._own_client:
            self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        """Close anchor session. Never delayed."""
        if self._own_client and self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None

    async def store_decision(self, receipt: DecisionReceipt) -> str:
        """Store a decision receipt in the hash chain.
        
        Args:
            receipt: Decision to record
            
        Returns:
            64-character hex hash of this decision
        """
        # Compute canonical JSON
        if receipt.decision_token:
            if receipt.decision_token in self._seen_tokens:
                raise ValueError("replay_detected")
            self._seen_tokens.add(receipt.decision_token)

        canonical = json.dumps(
            {
                "action": receipt.action,
                "reasoning": receipt.reasoning,
                "approved": receipt.approved,
                "timestamp": receipt.timestamp.isoformat(),
                "violations": sorted(receipt.policy_violations),
                "request_id": receipt.request_id,
                "policy_version": receipt.policy_version,
                "manifest_hash": receipt.manifest_hash,
                "fallback_state": receipt.fallback_state,
                "decision_token": receipt.decision_token,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        # Chain with previous
        prev_hash = self._chain_hashes[-1] if self._chain_hashes else ""
        new_hash = _helios_hash(canonical, prev_hash)

        # Update receipt
        receipt.helios_hash = new_hash

        # Append to local chain (never insert, never delete)
        self._decisions.append(receipt)
        self._chain_hashes.append(new_hash)
        self._persist_state()

        # Attempt Mneme persistence (best-effort)
        if self._client:
            try:
                await self._client.post(
                    f"{MNEME_URL}/decisions",
                    json={
                        "hash": new_hash,
                        "action": receipt.action,
                        "approved": receipt.approved,
                        "timestamp": receipt.timestamp.isoformat(),
                        "request_id": receipt.request_id,
                        "policy_version": receipt.policy_version,
                        "manifest_hash": receipt.manifest_hash,
                        "fallback_state": receipt.fallback_state,
                    },
                    headers={"Authorization": f"Bearer {MNEME_API_KEY}"}
                    if MNEME_API_KEY
                    else {},
                )
            except Exception:
                # Mneme persistence failure does NOT affect local chain
                pass

        return new_hash

    async def query_precedent(
        self,
        context: str,
        n: int = 5,
    ) -> list[DecisionReceipt]:
        """Query precedent decisions by action context.
        
        Args:
            context: Action description to search for
            n: Number of most recent results
            
        Returns:
            Most recent matching decisions (most recent first)
        """
        context_lower = context.lower()
        matching = [
            receipt for receipt in self._decisions
            if context_lower in receipt.action.lower()
        ]
        return list(reversed(matching))[:n]

    async def get_constitution(self) -> Constitution | None:
        """Get current constitutional framework."""
        return self._constitution

    async def verify_integrity(self) -> bool:
        """Verify integrity of the hash chain.
        
        NEVER self-repairs. Returns False if chain is broken.
        """
        if not self._chain_hashes:
            # Empty chain is valid
            return True

        # Rebuild chain and verify
        for i, receipt in enumerate(self._decisions):
            canonical = json.dumps(
                {
                    "action": receipt.action,
                    "reasoning": receipt.reasoning,
                    "approved": receipt.approved,
                    "timestamp": receipt.timestamp.isoformat(),
                    "violations": sorted(receipt.policy_violations),
                    "request_id": receipt.request_id,
                    "policy_version": receipt.policy_version,
                    "manifest_hash": receipt.manifest_hash,
                    "fallback_state": receipt.fallback_state,
                    "decision_token": receipt.decision_token,
                },
                sort_keys=True,
                separators=(",", ":"),
            )

            prev_hash = self._chain_hashes[i - 1] if i > 0 else ""
            expected_hash = _helios_hash(canonical, prev_hash)

            if expected_hash != self._chain_hashes[i]:
                return False

        return True

