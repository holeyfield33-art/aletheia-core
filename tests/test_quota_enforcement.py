"""Integration tests for API key auth + quota enforcement in bridge/fastapi_wrapper.py."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from core.key_store import KeyStore, _hash_key
from core.auth.models import AuthenticatedUser


_SAFE_PAYLOAD = "Generate the Q1 revenue report for the board"
_SAFE_ORIGIN = "trusted_admin"
_SAFE_ACTION = "Read_Report"


def _safe_body(ip: str = "10.99.0.1") -> dict:
    return {
        "payload": _SAFE_PAYLOAD,
        "origin": _SAFE_ORIGIN,
        "action": _SAFE_ACTION,
        "_ip": ip,
    }


def _post(
    client: TestClient, body: dict, api_key: str | None = None
) -> tuple[int, dict]:
    ip = body.pop("_ip", "10.99.0.1")
    headers: dict[str, str] = {"X-Forwarded-For": f"{ip}, 10.0.0.1"}
    if api_key:
        headers["X-API-Key"] = api_key
    r = client.post("/v1/audit", json=body, headers=headers)
    return r.status_code, r.json()


def _admin_headers() -> dict[str, str]:
    """Return headers that simulate an authenticated admin via OIDC bearer token."""
    return {"Authorization": "Bearer admin-test-token"}


def _admin_auth_mock():
    """Return a mock auth provider that authenticates admin users."""
    admin_user = AuthenticatedUser(
        user_id="test-admin",
        roles=frozenset({"admin", "operator"}),
        auth_method="oidc",
    )
    mock_provider = AsyncMock()
    mock_provider.authenticate.return_value = admin_user
    return mock_provider


class TestApiKeyAuth(unittest.TestCase):
    """API key authentication with the key store backend."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        cls._store = KeyStore(db_path=cls._tmp.name)

        # Create a trial key
        cls._raw_key, cls._record = cls._store.create_key("Test Trial Key")

        # Patch key store into the wrapper module (no env keys)
        # Also disable the global auth-disabled flag so key auth is enforced
        p1 = patch("bridge.fastapi_wrapper.key_store", cls._store)
        p2 = patch.dict(os.environ, {"ALETHEIA_AUTH_DISABLED": "false"})
        cls._patches = [p1, p2]
        for p in cls._patches:
            p.start()

        from bridge.fastapi_wrapper import app

        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls) -> None:
        for p in cls._patches:
            p.stop()
        os.unlink(cls._tmp.name)
        for ext in ("-wal", "-shm"):
            p = cls._tmp.name + ext
            if os.path.exists(p):
                os.unlink(p)

    def setUp(self) -> None:
        from core.rate_limit import rate_limiter
        from bridge.fastapi_wrapper import scout

        rate_limiter.reset()
        scout._query_history.clear()

    def test_missing_api_key_returns_401(self) -> None:
        status, body = _post(self.client, _safe_body("10.99.1.1"))
        self.assertEqual(status, 401)
        self.assertIn("error", body.get("detail", {}))

    def test_invalid_api_key_returns_401(self) -> None:
        status, body = _post(
            self.client, _safe_body("10.99.1.2"), api_key="sk_trial_bogus_key"
        )
        self.assertEqual(status, 401)

    def test_valid_trial_key_succeeds(self) -> None:
        status, body = _post(
            self.client, _safe_body("10.99.1.4"), api_key=self._raw_key
        )
        # Should succeed (200) or be policy-denied (403) — NOT 401
        self.assertIn(status, (200, 403))
        self.assertNotIn("unauthorized", str(body).lower())

    def test_usage_increments_after_request(self) -> None:
        initial = self._store.lookup_by_hash(self._raw_key)
        initial_used = initial.requests_used

        _post(self.client, _safe_body("10.99.1.5"), api_key=self._raw_key)

        updated = self._store.lookup_by_hash(self._raw_key)
        self.assertEqual(updated.requests_used, initial_used + 1)

    def test_revoked_key_returns_403(self) -> None:
        raw, record = self._store.create_key("Revoke Test")
        self._store.revoke_key(record.id)
        status, body = _post(self.client, _safe_body("10.99.1.6"), api_key=raw)
        self.assertEqual(status, 403)

    def test_quota_exceeded_returns_429(self) -> None:
        raw, record = self._store.create_key("Quota Test")
        # Max out the quota
        import sqlite3

        conn = sqlite3.connect(self._tmp.name)
        conn.execute(
            "UPDATE api_keys SET requests_used = monthly_quota WHERE key_hash = ?",
            (_hash_key(raw),),
        )
        conn.commit()
        conn.close()

        status, body = _post(self.client, _safe_body("10.99.1.7"), api_key=raw)
        self.assertEqual(status, 429)
        detail = body.get("detail", {})
        self.assertEqual(detail.get("error"), "quota_exceeded")
        self.assertIn("monthly request limit", detail.get("message", "").lower())


class TestKeyManagementEndpoints(unittest.TestCase):
    """Tests for /v1/keys management endpoints (RBAC-based auth)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp.close()
        cls._store = KeyStore(db_path=cls._tmp.name)

        cls._patches = [
            patch("bridge.fastapi_wrapper.key_store", cls._store),
        ]
        for p in cls._patches:
            p.start()

        from bridge.fastapi_wrapper import app

        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls) -> None:
        for p in cls._patches:
            p.stop()
        os.unlink(cls._tmp.name)
        for ext in ("-wal", "-shm"):
            p = cls._tmp.name + ext
            if os.path.exists(p):
                os.unlink(p)

    def test_create_key_requires_admin(self) -> None:
        r = self.client.post("/v1/keys", json={"name": "No Auth"})
        self.assertEqual(r.status_code, 401)

    def test_create_key_with_admin_auth(self) -> None:
        with patch(
            "bridge.fastapi_wrapper.get_auth_provider", return_value=_admin_auth_mock()
        ):
            r = self.client.post(
                "/v1/keys",
                json={"name": "Admin Created"},
                headers=_admin_headers(),
            )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertIn("key", data)
        self.assertTrue(data["key"].startswith("sk_trial_"))
        self.assertEqual(data["plan"], "trial")

    def test_list_keys_requires_admin(self) -> None:
        r = self.client.get("/v1/keys")
        self.assertEqual(r.status_code, 401)

    def test_list_keys_with_admin_auth(self) -> None:
        with patch(
            "bridge.fastapi_wrapper.get_auth_provider", return_value=_admin_auth_mock()
        ):
            # Create a key first
            self.client.post(
                "/v1/keys",
                json={"name": "Listed"},
                headers=_admin_headers(),
            )
            r = self.client.get("/v1/keys", headers=_admin_headers())
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("keys", data)
        self.assertGreater(len(data["keys"]), 0)
        # Ensure key_hash is not exposed
        for key in data["keys"]:
            self.assertNotIn("key_hash", key)

    def test_revoke_key_with_admin_auth(self) -> None:
        with patch(
            "bridge.fastapi_wrapper.get_auth_provider", return_value=_admin_auth_mock()
        ):
            r = self.client.post(
                "/v1/keys",
                json={"name": "To Revoke"},
                headers=_admin_headers(),
            )
            key_id = r.json()["id"]
            r = self.client.delete(
                f"/v1/keys/{key_id}",
                headers=_admin_headers(),
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "revoked")

    def test_revoke_nonexistent_key_returns_404(self) -> None:
        with patch(
            "bridge.fastapi_wrapper.get_auth_provider", return_value=_admin_auth_mock()
        ):
            r = self.client.delete(
                "/v1/keys/nonexistent_id",
                headers=_admin_headers(),
            )
        self.assertEqual(r.status_code, 404)

    def test_get_key_usage(self) -> None:
        with patch(
            "bridge.fastapi_wrapper.get_auth_provider", return_value=_admin_auth_mock()
        ):
            r = self.client.post(
                "/v1/keys",
                json={"name": "Usage Check"},
                headers=_admin_headers(),
            )
            key_id = r.json()["id"]
            r = self.client.get(
                f"/v1/keys/{key_id}/usage",
                headers=_admin_headers(),
            )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["name"], "Usage Check")
        self.assertEqual(data["requests_used"], 0)
        self.assertNotIn("key_hash", data)


if __name__ == "__main__":
    unittest.main()
