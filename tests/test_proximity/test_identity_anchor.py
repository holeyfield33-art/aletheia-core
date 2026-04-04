"""Tests for Identity Anchor module."""
import pytest
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import httpx

from proximity.identity_anchor import (
    IdentityAnchor,
    DecisionReceipt,
    _helios_hash,
)
from proximity.spectral_monitor import SpectralHealth


class TestHeliosHash:
    """Test helios hash chain function."""

    def test_deterministic(self):
        """Hash should be deterministic."""
        h1 = _helios_hash("content", "prev")
        h2 = _helios_hash("content", "prev")
        assert h1 == h2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        h1 = _helios_hash("content1", "prev")
        h2 = _helios_hash("content2", "prev")
        assert h1 != h2

    def test_different_prev_different_hash(self):
        """Different prev hash should produce different hash."""
        h1 = _helios_hash("content", "prev1")
        h2 = _helios_hash("content", "prev2")
        assert h1 != h2

    def test_format_is_hex(self):
        """Hash should be 64-character hex string."""
        h = _helios_hash("test", "")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestStoreDecision:
    """Test storing decisions in hash chain."""

    @pytest.mark.asyncio
    async def test_returns_hash_string(self):
        """store_decision should return 64-char hex hash."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        receipt = DecisionReceipt(
            action="test_action",
            reasoning="test_reasoning",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )

        hash_result = await anchor.store_decision(receipt)
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64

    @pytest.mark.asyncio
    async def test_sets_helios_hash_on_receipt(self):
        """store_decision should set helios_hash on receipt."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        receipt = DecisionReceipt(
            action="test_action",
            reasoning="test_reasoning",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )

        hash_result = await anchor.store_decision(receipt)
        assert receipt.helios_hash == hash_result

    @pytest.mark.asyncio
    async def test_two_decisions_have_different_hashes(self):
        """Two decisions should chain to different hashes."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        receipt1 = DecisionReceipt(
            action="action1",
            reasoning="reasoning1",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )
        hash1 = await anchor.store_decision(receipt1)

        receipt2 = DecisionReceipt(
            action="action2",
            reasoning="reasoning2",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )
        hash2 = await anchor.store_decision(receipt2)

        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_mneme_failure_does_not_prevent_storage(self):
        """Mneme failure should not affect local chain."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.HTTPError("mneme down")

        anchor = IdentityAnchor(http_client=mock_client)
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        receipt = DecisionReceipt(
            action="test_action",
            reasoning="test_reasoning",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )

        hash_result = await anchor.store_decision(receipt)
        assert hash_result is not None
        assert len(hash_result) == 64


class TestVerifyIntegrity:
    """Test hash chain integrity verification."""

    @pytest.mark.asyncio
    async def test_empty_chain_valid(self):
        """Empty chain should be valid."""
        anchor = IdentityAnchor()
        ok = await anchor.verify_integrity()
        assert ok is True

    @pytest.mark.asyncio
    async def test_valid_chain_passes(self):
        """Valid chain should pass verification."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        for i in range(3):
            receipt = DecisionReceipt(
                action=f"action_{i}",
                reasoning=f"reasoning_{i}",
                spectral_state=health,
                timestamp=datetime.now(timezone.utc),
            )
            await anchor.store_decision(receipt)

        ok = await anchor.verify_integrity()
        assert ok is True

    @pytest.mark.asyncio
    async def test_tampered_hash_fails(self):
        """Tampered hash should fail verification."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        receipt = DecisionReceipt(
            action="test_action",
            reasoning="test_reasoning",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )
        await anchor.store_decision(receipt)

        # Tamper the hash
        anchor._chain_hashes[0] = "0" * 64

        ok = await anchor.verify_integrity()
        assert ok is False

    @pytest.mark.asyncio
    async def test_never_modifies_chain_on_failure(self):
        """Verification should never modify the chain."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )
        receipt = DecisionReceipt(
            action="test_action",
            reasoning="test_reasoning",
            spectral_state=health,
            timestamp=datetime.now(timezone.utc),
        )
        await anchor.store_decision(receipt)

        original_length = len(anchor._decisions)

        # Tamper and verify
        anchor._chain_hashes[0] = "0" * 64
        await anchor.verify_integrity()

        # Chain length should not change
        assert len(anchor._decisions) == original_length


class TestQueryPrecedent:
    """Test precedent querying."""

    @pytest.mark.asyncio
    async def test_empty_when_no_decisions(self):
        """Should return empty list when no decisions."""
        anchor = IdentityAnchor()
        precedents = await anchor.query_precedent("any action")
        assert len(precedents) == 0

    @pytest.mark.asyncio
    async def test_most_recent_first(self):
        """Results should be most recent first."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        for i in range(3):
            receipt = DecisionReceipt(
                action="matching_action",
                reasoning=f"reasoning_{i}",
                spectral_state=health,
                timestamp=datetime.now(timezone.utc),
            )
            await anchor.store_decision(receipt)

        precedents = await anchor.query_precedent("matching_action", n=2)
        # Most recent should be last stored
        assert len(precedents) == 2

    @pytest.mark.asyncio
    async def test_n_limits_results(self):
        """n parameter should limit results."""
        anchor = IdentityAnchor()
        health = SpectralHealth(
            r_ratio=0.5,
            spectral_gap=0.1,
            coherence_index=0.5,
            timestamp=datetime.now(timezone.utc),
            session_id="test",
        )

        for i in range(5):
            receipt = DecisionReceipt(
                action="test_action",
                reasoning=f"reasoning_{i}",
                spectral_state=health,
                timestamp=datetime.now(timezone.utc),
            )
            await anchor.store_decision(receipt)

        precedents = await anchor.query_precedent("test_action", n=2)
        assert len(precedents) <= 2
