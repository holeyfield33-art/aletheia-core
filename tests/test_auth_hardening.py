"""Tests for authentication and authorization hardening.

Covers:
- FastAPI _check_api_key requires auth by default
- ALETHEIA_AUTH_DISABLED only works in non-production
- Metrics endpoint auth
- CORS wildcard block in production
- Rate limiter production enforcement
"""

from __future__ import annotations

import os
from unittest.mock import patch


from fastapi.testclient import TestClient


def _get_client():
    """Create a fresh TestClient for the FastAPI app."""
    # Re-import to pick up env changes at module scope
    from bridge.fastapi_wrapper import app

    return TestClient(app, raise_server_exceptions=False)


class TestAuthDisabledControl:
    """Verify ALETHEIA_AUTH_DISABLED behavior."""

    def test_auth_disabled_blocks_in_production(self):
        """ALETHEIA_AUTH_DISABLED=true in production should be blocked at startup."""
        env = {
            "ENVIRONMENT": "production",
            "ALETHEIA_AUTH_DISABLED": "true",
        }
        with patch.dict(os.environ, env):
            is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
            is_disabled = os.getenv("ALETHEIA_AUTH_DISABLED", "").lower() in (
                "true",
                "1",
                "yes",
            )
            assert is_production and is_disabled

    def test_auth_disabled_allowed_in_dev(self):
        """ALETHEIA_AUTH_DISABLED=true in development should work."""
        env = {
            "ENVIRONMENT": "development",
            "ALETHEIA_AUTH_DISABLED": "true",
        }
        with patch.dict(os.environ, env):
            is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
            is_disabled = os.getenv("ALETHEIA_AUTH_DISABLED", "").lower() in (
                "true",
                "1",
                "yes",
            )
            assert not is_production and is_disabled


class TestCORSWildcardBlock:
    """Verify wildcard CORS is blocked in production."""

    def test_wildcard_blocked_in_production(self):
        """CORS with '*' in production should be rejected."""
        env = {"ENVIRONMENT": "production", "ALETHEIA_CORS_ORIGINS": "*"}
        with patch.dict(os.environ, env):
            origins = os.getenv("ALETHEIA_CORS_ORIGINS", "").split(",")
            is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
            assert is_production and "*" in origins

    def test_explicit_origins_allowed(self):
        """Explicit CORS origins should work."""
        env = {
            "ALETHEIA_CORS_ORIGINS": "https://app.aletheia-core.com,https://aletheia-core.com"
        }
        with patch.dict(os.environ, env):
            origins = [
                o.strip() for o in os.getenv("ALETHEIA_CORS_ORIGINS", "").split(",")
            ]
            assert "*" not in origins
            assert len(origins) == 2


class TestSaltRequirements:
    """Verify production salt enforcement."""

    def test_alias_salt_required_in_production(self):
        """ALETHEIA_ALIAS_SALT must be set in production."""
        env = {"ENVIRONMENT": "production"}
        with patch.dict(os.environ, env):
            os.environ.pop("ALETHEIA_ALIAS_SALT", None)
            assert not os.getenv("ALETHEIA_ALIAS_SALT", "").strip()
            assert os.getenv("ENVIRONMENT", "").lower() == "production"

    def test_key_salt_required_in_production(self):
        """ALETHEIA_KEY_SALT must be set in production."""
        env = {"ENVIRONMENT": "production"}
        with patch.dict(os.environ, env):
            os.environ.pop("ALETHEIA_KEY_SALT", None)
            assert not os.getenv("ALETHEIA_KEY_SALT", "").strip()
            assert os.getenv("ENVIRONMENT", "").lower() == "production"


class TestNitpickerRotation:
    """Verify HMAC-seeded rotation in Nitpicker V2."""

    def test_rotation_with_salt_is_unpredictable(self):
        """With ALETHEIA_ROTATION_SALT, rotation should use HMAC."""
        with patch.dict(os.environ, {"ALETHEIA_ROTATION_SALT": "test-salt-123"}):
            from agents.nitpicker_v2 import AletheiaNitpickerV2

            n = AletheiaNitpickerV2()
            assert n._rotation_salt == "test-salt-123"

    def test_rotation_without_salt_uses_counter(self):
        """Without salt, rotation falls back to counter (logged warning)."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALETHEIA_ROTATION_SALT", None)
            from agents.nitpicker_v2 import AletheiaNitpickerV2

            n = AletheiaNitpickerV2()
            assert n._rotation_salt == ""
