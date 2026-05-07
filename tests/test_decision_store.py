"""Tests for core/decision_store.py — SQLite backend and DecisionStore facade."""
from __future__ import annotations

import importlib
import os
import pytest


# ---------------------------------------------------------------------------
# _SQLiteDecisionStore (low-level)
# ---------------------------------------------------------------------------


class TestSQLiteDecisionStore:
    @pytest.fixture
    def store(self, tmp_path):
        from core.decision_store import _SQLiteDecisionStore

        return _SQLiteDecisionStore(db_path=str(tmp_path / "test_decisions.sqlite3"))

    def test_backend_name_is_sqlite(self, store):
        assert store.backend == "sqlite"

    @pytest.mark.asyncio
    async def test_claim_token_accepts_new_token(self, store):
        result = await store.claim_token(
            token="tok1",
            request_id="req1",
            policy_version="v1.0",
            manifest_hash="abc123",
            now_ts=1000,
            ttl_seconds=3600,
        )
        assert result.accepted is True
        assert result.reason == "accepted"

    @pytest.mark.asyncio
    async def test_claim_token_detects_replay(self, store):
        kwargs = dict(
            token="tok1",
            request_id="req1",
            policy_version="v1.0",
            manifest_hash="abc123",
            now_ts=1000,
            ttl_seconds=3600,
        )
        await store.claim_token(**kwargs)
        result = await store.claim_token(**kwargs)
        assert result.accepted is False
        assert result.reason == "replay_detected"

    @pytest.mark.asyncio
    async def test_expired_tokens_are_pruned_allowing_reuse(self, store):
        await store.claim_token(
            token="expiring_tok",
            request_id="req-old",
            policy_version="v1",
            manifest_hash="h1",
            now_ts=100,
            ttl_seconds=1,  # expires at ts=101
        )
        # now_ts=200 > 101, so the record is pruned; same token allowed again
        result = await store.claim_token(
            token="expiring_tok",
            request_id="req-new",
            policy_version="v1",
            manifest_hash="h1",
            now_ts=200,
            ttl_seconds=3600,
        )
        assert result.accepted is True

    @pytest.mark.asyncio
    async def test_verify_bundle_registers_new_bundle(self, store):
        result = await store.verify_bundle(
            policy_version="v1.0",
            manifest_hash="abc123",
            now_ts=1000,
        )
        assert result.accepted is True
        assert result.reason == "bundle_registered"

    @pytest.mark.asyncio
    async def test_verify_bundle_confirms_same_bundle(self, store):
        await store.verify_bundle(
            policy_version="v1.0", manifest_hash="abc123", now_ts=1000
        )
        result = await store.verify_bundle(
            policy_version="v1.0", manifest_hash="abc123", now_ts=2000
        )
        assert result.accepted is True
        assert result.reason == "bundle_verified"

    @pytest.mark.asyncio
    async def test_verify_bundle_detects_version_drift(self, store):
        await store.verify_bundle(
            policy_version="v1.0", manifest_hash="abc123", now_ts=1000
        )
        result = await store.verify_bundle(
            policy_version="v1.1", manifest_hash="abc123", now_ts=2000
        )
        assert result.accepted is False
        assert result.reason == "partial_deployment_drift"

    @pytest.mark.asyncio
    async def test_verify_bundle_detects_hash_drift(self, store):
        await store.verify_bundle(
            policy_version="v1.0", manifest_hash="hash-a", now_ts=1000
        )
        result = await store.verify_bundle(
            policy_version="v1.0", manifest_hash="hash-b", now_ts=2000
        )
        assert result.accepted is False
        assert result.reason == "partial_deployment_drift"

    @pytest.mark.asyncio
    async def test_tenant_isolation_for_tokens(self, store):
        result_a = await store.claim_token(
            token="shared_tok",
            request_id="req-a",
            policy_version="v1",
            manifest_hash="h1",
            now_ts=1000,
            tenant_id="tenant_a",
        )
        result_b = await store.claim_token(
            token="shared_tok",
            request_id="req-b",
            policy_version="v1",
            manifest_hash="h1",
            now_ts=1000,
            tenant_id="tenant_b",
        )
        assert result_a.accepted is True
        assert result_b.accepted is True

    @pytest.mark.asyncio
    async def test_same_tenant_detects_replay(self, store):
        kwargs = dict(
            token="tok-same",
            request_id="req",
            policy_version="v1",
            manifest_hash="h",
            now_ts=1000,
            tenant_id="tenant_x",
        )
        await store.claim_token(**kwargs)
        result = await store.claim_token(**kwargs)
        assert result.accepted is False

    @pytest.mark.asyncio
    async def test_tenant_bundle_isolation(self, store):
        await store.verify_bundle(
            policy_version="v1",
            manifest_hash="hash-a",
            now_ts=1000,
            tenant_id="t1",
        )
        result = await store.verify_bundle(
            policy_version="v2",
            manifest_hash="hash-b",
            now_ts=1000,
            tenant_id="t2",  # different tenant
        )
        assert result.accepted is True


# ---------------------------------------------------------------------------
# DecisionStore (facade)
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_sqlite_store(tmp_path, monkeypatch):
    monkeypatch.setenv("ALETHEIA_DECISION_DB_PATH", str(tmp_path / "ds.sqlite3"))
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    import core.decision_store as ds_mod

    importlib.reload(ds_mod)
    return ds_mod.DecisionStore()


class TestDecisionStoreFacade:
    def test_backend_is_sqlite_without_upstash(self, fresh_sqlite_store):
        assert fresh_sqlite_store.backend == "sqlite"

    def test_not_degraded_initially(self, fresh_sqlite_store):
        assert fresh_sqlite_store.degraded is False

    @pytest.mark.asyncio
    async def test_claim_decision_accepted(self, fresh_sqlite_store):
        result = await fresh_sqlite_store.claim_decision(
            request_id="req-1",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
        )
        assert result.accepted is True

    @pytest.mark.asyncio
    async def test_claim_decision_replay_rejected(self, fresh_sqlite_store):
        kwargs = dict(
            request_id="req-2",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
        )
        await fresh_sqlite_store.claim_decision(**kwargs)
        result = await fresh_sqlite_store.claim_decision(**kwargs)
        assert result.accepted is False
        assert result.reason == "replay_detected"

    @pytest.mark.asyncio
    async def test_token_is_deterministic_from_inputs(self, fresh_sqlite_store):
        kwargs = dict(
            request_id="req-determinism",
            timestamp_iso="2026-05-07T12:00:00Z",
            policy_version="v1.9",
            manifest_hash="deadbeef",
        )
        r1 = await fresh_sqlite_store.claim_decision(**kwargs)
        r2 = await fresh_sqlite_store.claim_decision(**kwargs)
        assert r1.accepted is True
        assert r2.accepted is False  # same token derived from same inputs

    @pytest.mark.asyncio
    async def test_different_request_ids_both_accepted(self, fresh_sqlite_store):
        r1 = await fresh_sqlite_store.claim_decision(
            request_id="req-A",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
        )
        r2 = await fresh_sqlite_store.claim_decision(
            request_id="req-B",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
        )
        assert r1.accepted is True
        assert r2.accepted is True

    @pytest.mark.asyncio
    async def test_verify_policy_bundle_accepted(self, fresh_sqlite_store):
        result = await fresh_sqlite_store.verify_policy_bundle("v1", "hash1")
        assert result.accepted is True

    @pytest.mark.asyncio
    async def test_marks_degraded_on_store_error(self, fresh_sqlite_store, monkeypatch):
        async def raise_error(**kwargs):
            raise RuntimeError("injected failure")

        monkeypatch.setattr(fresh_sqlite_store._store, "claim_token", raise_error)
        result = await fresh_sqlite_store.claim_decision(
            request_id="r",
            timestamp_iso="t",
            policy_version="v",
            manifest_hash="h",
        )
        assert result.accepted is False
        assert result.reason == "decision_store_unavailable"
        assert fresh_sqlite_store.degraded is True

    @pytest.mark.asyncio
    async def test_bundle_verification_error_marks_degraded(
        self, fresh_sqlite_store, monkeypatch
    ):
        async def raise_error(**kwargs):
            raise RuntimeError("bundle store down")

        monkeypatch.setattr(fresh_sqlite_store._store, "verify_bundle", raise_error)
        result = await fresh_sqlite_store.verify_policy_bundle("v1", "h1")
        assert result.accepted is False
        assert fresh_sqlite_store.degraded is True

    @pytest.mark.asyncio
    async def test_tenant_scoped_claim(self, fresh_sqlite_store):
        r1 = await fresh_sqlite_store.claim_decision(
            request_id="req",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
            tenant_id="acme",
        )
        r2 = await fresh_sqlite_store.claim_decision(
            request_id="req",
            timestamp_iso="2026-01-01T00:00:00Z",
            policy_version="v1",
            manifest_hash="h1",
            tenant_id="globex",  # different tenant
        )
        assert r1.accepted is True
        assert r2.accepted is True
