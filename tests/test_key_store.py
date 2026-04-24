"""Tests for core/key_store.py — API key lifecycle and quota enforcement."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

from core.key_store import KeyStore, DEFAULT_QUOTAS, _hash_key


class _KeyStoreTestBase(unittest.TestCase):
    """Base class that creates a fresh SQLite key store per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.store = KeyStore(db_path=self._tmp.name)

    def tearDown(self) -> None:
        os.unlink(self._tmp.name)
        wal = self._tmp.name + "-wal"
        shm = self._tmp.name + "-shm"
        if os.path.exists(wal):
            os.unlink(wal)
        if os.path.exists(shm):
            os.unlink(shm)


class TestKeyCreation(_KeyStoreTestBase):
    """Key creation and storage safety."""

    def test_create_returns_raw_key_and_record(self) -> None:
        raw, record = self.store.create_key("Test Key")
        self.assertTrue(raw.startswith("sk_trial_"))
        self.assertEqual(record.name, "Test Key")
        self.assertEqual(record.plan, "trial")
        self.assertEqual(record.status, "active")

    def test_raw_key_is_not_stored(self) -> None:
        raw, record = self.store.create_key("My Key")
        # Record hash should match the hash of the raw key
        self.assertEqual(record.key_hash, _hash_key(raw))
        # But the raw key itself is not in the record prefix
        self.assertNotEqual(record.key_prefix, raw)
        self.assertIn("...", record.key_prefix)

    def test_prefix_contains_partial_key(self) -> None:
        raw, record = self.store.create_key("Prefixed")
        # Prefix = first 12 chars + "..." + last 4 chars
        self.assertTrue(record.key_prefix.startswith(raw[:12]))
        self.assertTrue(record.key_prefix.endswith(raw[-4:]))

    def test_trial_plan_quota(self) -> None:
        _, record = self.store.create_key("Trial", plan="trial")
        self.assertEqual(record.monthly_quota, DEFAULT_QUOTAS["trial"])

    def test_pro_plan_quota(self) -> None:
        _, record = self.store.create_key("Pro", plan="pro")
        self.assertEqual(record.monthly_quota, DEFAULT_QUOTAS["pro"])

    def test_max_plan_quota(self) -> None:
        _, record = self.store.create_key("Max", plan="max")
        self.assertEqual(record.monthly_quota, DEFAULT_QUOTAS["max"])

    def test_invalid_plan_defaults_to_trial(self) -> None:
        _, record = self.store.create_key("Bad Plan", plan="enterprise")
        self.assertEqual(record.plan, "trial")

    def test_requests_used_starts_at_zero(self) -> None:
        _, record = self.store.create_key("Fresh")
        self.assertEqual(record.requests_used, 0)

    def test_period_boundaries_set(self) -> None:
        _, record = self.store.create_key("Dated")
        start = datetime.fromisoformat(record.period_start)
        end = datetime.fromisoformat(record.period_end)
        self.assertLess(start, end)
        self.assertEqual(start.day, 1)

    def test_unique_key_ids(self) -> None:
        _, r1 = self.store.create_key("A")
        _, r2 = self.store.create_key("B")
        self.assertNotEqual(r1.id, r2.id)


class TestKeyLookup(_KeyStoreTestBase):
    """Key lookup and listing."""

    def test_lookup_by_hash_found(self) -> None:
        raw, created = self.store.create_key("Lookup")
        found = self.store.lookup_by_hash(raw)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, created.id)

    def test_lookup_by_hash_not_found(self) -> None:
        result = self.store.lookup_by_hash("sk_trial_nonexistent")
        self.assertIsNone(result)

    def test_get_by_id(self) -> None:
        _, created = self.store.create_key("ById")
        found = self.store.get_by_id(created.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "ById")

    def test_list_keys(self) -> None:
        self.store.create_key("First")
        self.store.create_key("Second")
        keys = self.store.list_keys()
        self.assertEqual(len(keys), 2)

    def test_list_keys_ordered_newest_first(self) -> None:
        self.store.create_key("Old")
        self.store.create_key("New")
        keys = self.store.list_keys()
        self.assertEqual(keys[0].name, "New")


class TestKeyRevocation(_KeyStoreTestBase):
    """Key revocation."""

    def test_revoke_active_key(self) -> None:
        _, record = self.store.create_key("Revoke Me")
        success = self.store.revoke_key(record.id)
        self.assertTrue(success)
        updated = self.store.get_by_id(record.id)
        self.assertEqual(updated.status, "revoked")

    def test_revoke_already_revoked(self) -> None:
        _, record = self.store.create_key("Already Revoked")
        self.store.revoke_key(record.id)
        success = self.store.revoke_key(record.id)
        self.assertFalse(success)

    def test_revoke_nonexistent(self) -> None:
        success = self.store.revoke_key("nonexistent_id")
        self.assertFalse(success)


class TestQuotaEnforcement(_KeyStoreTestBase):
    """Quota checking and enforcement."""

    def test_valid_key_allowed(self) -> None:
        raw, _ = self.store.create_key("Valid")
        result = self.store.check_and_increment(raw)
        self.assertTrue(result.allowed)
        self.assertEqual(result.reason, "OK")
        self.assertEqual(result.requests_used, 1)

    def test_invalid_key_rejected(self) -> None:
        result = self.store.check_and_increment("sk_trial_invalid_key")
        self.assertFalse(result.allowed)
        self.assertIn("Invalid", result.reason)

    def test_revoked_key_rejected(self) -> None:
        raw, record = self.store.create_key("Revoked")
        self.store.revoke_key(record.id)
        result = self.store.check_and_increment(raw)
        self.assertFalse(result.allowed)
        self.assertIn("revoked", result.reason.lower())

    def test_usage_increments(self) -> None:
        raw, _ = self.store.create_key("Counter")
        self.store.check_and_increment(raw)
        self.store.check_and_increment(raw)
        result = self.store.check_and_increment(raw)
        self.assertTrue(result.allowed)
        self.assertEqual(result.requests_used, 3)

    def test_quota_exceeded(self) -> None:
        raw, _ = self.store.create_key("Quota")
        # Manually set usage to max
        import sqlite3

        conn = sqlite3.connect(self._tmp.name)
        conn.execute(
            "UPDATE api_keys SET requests_used = monthly_quota WHERE key_hash = ?",
            (_hash_key(raw),),
        )
        conn.commit()
        conn.close()

        result = self.store.check_and_increment(raw)
        self.assertFalse(result.allowed)
        self.assertIn("monthly request limit", result.reason.lower())

    def test_last_used_at_updated(self) -> None:
        raw, record = self.store.create_key("LastUsed")
        self.assertIsNone(record.last_used_at)
        self.store.check_and_increment(raw)
        updated = self.store.lookup_by_hash(raw)
        self.assertIsNotNone(updated.last_used_at)


class TestBillingPeriodReset(_KeyStoreTestBase):
    """Billing period reset when period has expired."""

    def test_period_reset_clears_usage(self) -> None:
        raw, _ = self.store.create_key("Reset")
        # Use some quota
        self.store.check_and_increment(raw)
        self.store.check_and_increment(raw)

        # Manually set period_end to the past
        import sqlite3

        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        conn = sqlite3.connect(self._tmp.name)
        conn.execute(
            "UPDATE api_keys SET period_end = ? WHERE key_hash = ?",
            (past, _hash_key(raw)),
        )
        conn.commit()
        conn.close()

        # Next check should reset
        result = self.store.check_and_increment(raw)
        self.assertTrue(result.allowed)
        # Usage reset to 0, then incremented to 1
        self.assertEqual(result.requests_used, 1)

    def test_period_boundaries_updated_after_reset(self) -> None:
        raw, _ = self.store.create_key("NewPeriod")

        import sqlite3

        past = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        conn = sqlite3.connect(self._tmp.name)
        conn.execute(
            "UPDATE api_keys SET period_end = ?, requests_used = 500 WHERE key_hash = ?",
            (past, _hash_key(raw)),
        )
        conn.commit()
        conn.close()

        self.store.check_and_increment(raw)
        record = self.store.lookup_by_hash(raw)
        new_start = datetime.fromisoformat(record.period_start)
        new_end = datetime.fromisoformat(record.period_end)
        now = datetime.now(timezone.utc)
        # New period should be the current month
        self.assertEqual(new_start.month, now.month)
        self.assertGreater(new_end, now)


class TestPublicDict(_KeyStoreTestBase):
    """to_public_dict must not expose key_hash."""

    def test_no_hash_in_public_dict(self) -> None:
        _, record = self.store.create_key("Public")
        d = record.to_public_dict()
        self.assertNotIn("key_hash", d)
        self.assertIn("id", d)
        self.assertIn("plan", d)


if __name__ == "__main__":
    unittest.main()
