from __future__ import annotations

import os
import tempfile

import pytest

from core.decision_store import DecisionStore


@pytest.mark.asyncio
async def test_replay_rejected_for_same_token() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "decisions.sqlite")
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("UPSTASH_REDIS_REST_URL", raising=False)
            mp.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
            mp.setenv("ALETHEIA_DECISION_DB_PATH", db_path)
            store = DecisionStore()

            first = await store.claim_decision(
                request_id="req-1",
                timestamp_iso="2026-04-07T00:00:00+00:00",
                policy_version="2026.03.07",
                manifest_hash="abc",
            )
            second = await store.claim_decision(
                request_id="req-1",
                timestamp_iso="2026-04-07T00:00:00+00:00",
                policy_version="2026.03.07",
                manifest_hash="abc",
            )

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "replay_detected"


@pytest.mark.asyncio
async def test_restart_recovery_keeps_replay_protection() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "decisions.sqlite")
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("UPSTASH_REDIS_REST_URL", raising=False)
            mp.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
            mp.setenv("ALETHEIA_DECISION_DB_PATH", db_path)

            store1 = DecisionStore()
            accepted = await store1.claim_decision(
                request_id="req-restart",
                timestamp_iso="2026-04-07T00:00:01+00:00",
                policy_version="2026.03.07",
                manifest_hash="hash-a",
            )
            store2 = DecisionStore()
            replay = await store2.claim_decision(
                request_id="req-restart",
                timestamp_iso="2026-04-07T00:00:01+00:00",
                policy_version="2026.03.07",
                manifest_hash="hash-a",
            )

    assert accepted.accepted is True
    assert replay.accepted is False


@pytest.mark.asyncio
async def test_partial_deployment_drift_detected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "decisions.sqlite")
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("UPSTASH_REDIS_REST_URL", raising=False)
            mp.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
            mp.setenv("ALETHEIA_DECISION_DB_PATH", db_path)
            store = DecisionStore()

            baseline = await store.verify_policy_bundle("2026.03.07", "hash-a")
            drift = await store.verify_policy_bundle("2026.03.08", "hash-b")

    assert baseline.accepted is True
    assert drift.accepted is False
    assert drift.reason == "partial_deployment_drift"
