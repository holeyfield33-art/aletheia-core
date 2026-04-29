"""Tests for the pluggable auth layer (core/auth/) and RBAC (core/auth/rbac.py).

Covers:
  - APIKeyAuthProvider (env keys, admin promotion)
  - Auth factory (get_auth_provider / reset_auth_provider)
  - RBAC permission matrix exhaustive check
  - require_permission / require_role FastAPI dependencies
"""

from __future__ import annotations

import os
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from core.auth import get_auth_provider, reset_auth_provider
from core.auth.api_key import APIKeyAuthProvider
from core.auth.models import AuthenticatedUser, AuthContext
from core.auth.rbac import (
    Permission,
    has_permission,
    require_permission,
    require_role,
)


# ---------------------------------------------------------------------------
# APIKeyAuthProvider
# ---------------------------------------------------------------------------


class TestAPIKeyAuthProvider:
    @pytest.fixture(autouse=True)
    def _env(self):
        orig = os.environ.copy()
        # Env keys are no longer supported; ensure they're not set
        os.environ.pop("ALETHEIA_API_KEYS", None)
        os.environ.pop("ALETHEIA_ADMIN_KEY", None)
        yield
        os.environ.clear()
        os.environ.update(orig)

    @pytest.fixture
    def provider(self) -> APIKeyAuthProvider:
        return APIKeyAuthProvider()

    @pytest.mark.asyncio
    async def test_keystore_key_authenticates(self, provider):
        """KeyStore keys authenticate successfully."""
        from unittest.mock import MagicMock

        mock_quota = MagicMock(allowed=True)
        mock_record = MagicMock(id="key-123", role="operator")
        with patch("core.key_store.key_store") as ks:
            ks.check_and_increment.return_value = mock_quota
            ks.lookup_by_hash.return_value = mock_record
            user = await provider.authenticate("sk_trial_some_key")
        assert user is not None
        assert user.auth_method == "api_key"
        assert "operator" in user.roles

    @pytest.mark.asyncio
    async def test_admin_role_from_keystore(self, provider):
        """KeyStore key with admin role gets admin access."""
        from unittest.mock import MagicMock

        mock_quota = MagicMock(allowed=True)
        mock_record = MagicMock(id="key-admin", role="admin")
        with patch("core.key_store.key_store") as ks:
            ks.check_and_increment.return_value = mock_quota
            ks.lookup_by_hash.return_value = mock_record
            user = await provider.authenticate("sk_pro_admin_key")
        assert user is not None
        assert "admin" in user.roles

    @pytest.mark.asyncio
    async def test_env_keys_rejected_in_production(self):
        """Setting ALETHEIA_API_KEYS in production raises RuntimeError."""
        os.environ["ALETHEIA_API_KEYS"] = "key1,key2"
        os.environ["ENVIRONMENT"] = "production"
        with pytest.raises(RuntimeError, match="ALETHEIA_API_KEYS"):
            APIKeyAuthProvider()

    @pytest.mark.asyncio
    async def test_env_keys_ignored_in_dev(self):
        """Env keys are silently ignored in non-production mode."""
        os.environ["ALETHEIA_API_KEYS"] = "key1,key2"
        os.environ["ENVIRONMENT"] = "development"
        provider = APIKeyAuthProvider()
        assert provider is not None

    @pytest.mark.asyncio
    async def test_empty_credential_returns_none(self, provider):
        assert await provider.authenticate("") is None

    @pytest.mark.asyncio
    async def test_unknown_key_returns_none(self, provider):
        # Patch key_store to avoid SQLite side-effects
        mock_quota = MagicMock(allowed=False)
        with patch("core.key_store.key_store") as ks:
            ks.check_and_increment.return_value = mock_quota
            result = await provider.authenticate("bad-key")
        assert result is None


# ---------------------------------------------------------------------------
# Auth factory
# ---------------------------------------------------------------------------


class TestAuthFactory:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_auth_provider()
        yield
        reset_auth_provider()

    def test_default_is_api_key(self):
        provider = get_auth_provider()
        assert isinstance(provider, APIKeyAuthProvider)

    def test_singleton(self):
        a = get_auth_provider()
        b = get_auth_provider()
        assert a is b

    def test_reset_clears_singleton(self):
        a = get_auth_provider()
        reset_auth_provider()
        b = get_auth_provider()
        assert a is not b

    def test_invalid_provider_raises(self):
        from core.config import settings

        orig = settings.auth_provider
        try:
            settings.auth_provider = "nosuch"
            with pytest.raises(ValueError, match="Unknown auth provider"):
                get_auth_provider()
        finally:
            settings.auth_provider = orig


# ---------------------------------------------------------------------------
# RBAC — Permission matrix
# ---------------------------------------------------------------------------


class TestPermissionMatrix:
    """Exhaustive check: every role / permission combination."""

    def test_admin_has_all_permissions(self):
        for perm in Permission:
            assert has_permission(frozenset({"admin"}), perm), f"admin missing {perm}"

    def test_viewer_has_only_keys_list(self):
        for perm in Permission:
            expected = perm == Permission.KEYS_LIST
            assert has_permission(frozenset({"viewer"}), perm) == expected, (
                f"viewer + {perm} should be {expected}"
            )

    def test_auditor_permissions(self):
        expected = {
            Permission.AUDIT_READ,
            Permission.KEYS_LIST,
            Permission.KEYS_USAGE,
            Permission.METRICS_READ,
            Permission.HEALTH_FULL,
        }
        for perm in Permission:
            assert has_permission(frozenset({"auditor"}), perm) == (perm in expected), (
                f"auditor + {perm}"
            )

    def test_operator_permissions(self):
        expected = {
            Permission.AUDIT_SUBMIT,
            Permission.AUDIT_READ,
            Permission.KEYS_LIST,
            Permission.KEYS_USAGE,
            Permission.METRICS_READ,
            Permission.HEALTH_FULL,
        }
        for perm in Permission:
            assert has_permission(frozenset({"operator"}), perm) == (
                perm in expected
            ), f"operator + {perm}"

    def test_combined_roles_union(self):
        """Multiple roles → union of their permissions."""
        assert has_permission(frozenset({"viewer", "auditor"}), Permission.AUDIT_READ)
        assert has_permission(frozenset({"viewer", "auditor"}), Permission.KEYS_LIST)

    def test_unknown_role_has_no_permissions(self):
        for perm in Permission:
            assert not has_permission(frozenset({"rogue"}), perm)


# ---------------------------------------------------------------------------
# RBAC — FastAPI dependencies
# ---------------------------------------------------------------------------


class TestRBACDependencies:
    def _make_request(self, user: AuthenticatedUser | None):
        """Create a mock Request with auth_context."""
        request = MagicMock()
        if user:
            request.state.auth_context = AuthContext(user=user)
        else:
            request.state = SimpleNamespace()  # no auth_context attr
        return request

    @pytest.mark.asyncio
    async def test_require_permission_passes(self):
        user = AuthenticatedUser(
            user_id="u1", roles=frozenset({"admin"}), auth_method="api_key"
        )
        request = self._make_request(user)
        dep = require_permission(Permission.KEYS_CREATE)
        await dep(request)  # should not raise

    @pytest.mark.asyncio
    async def test_require_permission_denies(self):
        from fastapi import HTTPException

        user = AuthenticatedUser(
            user_id="u1", roles=frozenset({"viewer"}), auth_method="api_key"
        )
        request = self._make_request(user)
        dep = require_permission(Permission.KEYS_CREATE)
        with pytest.raises(HTTPException) as exc_info:
            await dep(request)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_permission_unauthenticated(self):
        from fastapi import HTTPException

        request = self._make_request(None)
        dep = require_permission(Permission.AUDIT_SUBMIT)
        with pytest.raises(HTTPException) as exc_info:
            await dep(request)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_role_passes(self):
        user = AuthenticatedUser(
            user_id="u1", roles=frozenset({"operator"}), auth_method="api_key"
        )
        request = self._make_request(user)
        dep = require_role("operator", "admin")
        await dep(request)  # should not raise

    @pytest.mark.asyncio
    async def test_require_role_denies(self):
        from fastapi import HTTPException

        user = AuthenticatedUser(
            user_id="u1", roles=frozenset({"viewer"}), auth_method="api_key"
        )
        request = self._make_request(user)
        dep = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await dep(request)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# AuthenticatedUser model
# ---------------------------------------------------------------------------


class TestAuthenticatedUser:
    def test_primary_role_picks_highest_privilege(self):
        user = AuthenticatedUser(
            user_id="u", roles=frozenset({"viewer", "admin"}), auth_method="x"
        )
        assert user.primary_role == "admin"

    def test_is_admin(self):
        user = AuthenticatedUser(
            user_id="u", roles=frozenset({"admin"}), auth_method="x"
        )
        assert user.is_admin

    def test_is_not_admin(self):
        user = AuthenticatedUser(
            user_id="u", roles=frozenset({"operator"}), auth_method="x"
        )
        assert not user.is_admin

    def test_frozen(self):
        user = AuthenticatedUser(
            user_id="u", roles=frozenset({"viewer"}), auth_method="x"
        )
        with pytest.raises(AttributeError):
            user.user_id = "changed"
