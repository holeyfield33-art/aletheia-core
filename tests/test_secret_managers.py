"""Tests for the pluggable secret-manager layer (core/secrets/).

Covers:
  - EnvSecretManager (full coverage — no mocks needed)
  - Factory function (get_secret_manager / reset_secret_manager)
  - Invalid backend rejection
  - Cloud backends (import gate only — no live cloud calls)
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch

from core.secrets import get_secret_manager, reset_secret_manager
from core.secrets.env import EnvSecretManager


# ---------------------------------------------------------------------------
# EnvSecretManager
# ---------------------------------------------------------------------------


class TestEnvSecretManager:
    """Full async coverage of the environment-variable backend."""

    @pytest.fixture(autouse=True)
    def _clean_env(self):
        """Ensure test env vars don't leak."""
        keys = [
            "ALETHEIA_TEST_SECRET",
            "ALETHEIA_ANOTHER_SECRET",
        ]
        for k in keys:
            os.environ.pop(k, None)
        yield
        for k in keys:
            os.environ.pop(k, None)

    @pytest.fixture
    def sm(self) -> EnvSecretManager:
        return EnvSecretManager()

    @pytest.mark.asyncio
    async def test_get_secret_missing(self, sm: EnvSecretManager) -> None:
        result = await sm.get_secret("TEST_SECRET")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_secret(self, sm: EnvSecretManager) -> None:
        await sm.set_secret("TEST_SECRET", "my_value")
        assert os.environ.get("ALETHEIA_TEST_SECRET") == "my_value"
        result = await sm.get_secret("TEST_SECRET")
        assert result == "my_value"

    @pytest.mark.asyncio
    async def test_get_secret_with_full_prefix(self, sm: EnvSecretManager) -> None:
        """Keys already prefixed with ALETHEIA_ should not get double-prefixed."""
        os.environ["ALETHEIA_TEST_SECRET"] = "hello"
        result = await sm.get_secret("ALETHEIA_TEST_SECRET")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_delete_secret(self, sm: EnvSecretManager) -> None:
        os.environ["ALETHEIA_TEST_SECRET"] = "to_delete"
        await sm.delete_secret("TEST_SECRET")
        assert "ALETHEIA_TEST_SECRET" not in os.environ

    @pytest.mark.asyncio
    async def test_delete_nonexistent_is_noop(self, sm: EnvSecretManager) -> None:
        await sm.delete_secret("NONEXISTENT_SECRET")  # should not raise

    @pytest.mark.asyncio
    async def test_list_secrets(self, sm: EnvSecretManager) -> None:
        os.environ["ALETHEIA_TEST_SECRET"] = "a"
        os.environ["ALETHEIA_ANOTHER_SECRET"] = "b"
        names = await sm.list_secrets()
        assert "ALETHEIA_TEST_SECRET" in names
        assert "ALETHEIA_ANOTHER_SECRET" in names

    @pytest.mark.asyncio
    async def test_list_secrets_with_prefix(self, sm: EnvSecretManager) -> None:
        os.environ["ALETHEIA_TEST_SECRET"] = "a"
        names = await sm.list_secrets("TEST")
        assert "ALETHEIA_TEST_SECRET" in names
        assert "ALETHEIA_ANOTHER_SECRET" not in names

    @pytest.mark.asyncio
    async def test_health_check(self, sm: EnvSecretManager) -> None:
        assert await sm.health_check() is True

    @pytest.mark.asyncio
    async def test_get_secret_or_default(self, sm: EnvSecretManager) -> None:
        result = await sm.get_secret_or_default("NONEXISTENT", "fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_get_empty_value_returns_none(self, sm: EnvSecretManager) -> None:
        os.environ["ALETHEIA_TEST_SECRET"] = "   "
        result = await sm.get_secret("TEST_SECRET")
        assert result is None  # whitespace-only treated as missing


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestSecretManagerFactory:
    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_secret_manager()
        yield
        reset_secret_manager()

    def test_default_backend_is_env(self) -> None:
        with patch.dict(os.environ, {"ALETHEIA_SECRET_BACKEND": "env"}, clear=False):
            sm = get_secret_manager()
            assert isinstance(sm, EnvSecretManager)

    def test_missing_backend_env_defaults_to_env(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALETHEIA_SECRET_BACKEND", None)
            sm = get_secret_manager()
            assert isinstance(sm, EnvSecretManager)

    def test_invalid_backend_raises(self) -> None:
        with patch.dict(os.environ, {"ALETHEIA_SECRET_BACKEND": "nosuch"}, clear=False):
            with pytest.raises(ValueError, match="Unknown secret backend"):
                get_secret_manager()

    def test_singleton_returns_same_instance(self) -> None:
        sm1 = get_secret_manager()
        sm2 = get_secret_manager()
        assert sm1 is sm2

    def test_reset_clears_singleton(self) -> None:
        sm1 = get_secret_manager()
        reset_secret_manager()
        # Force re-creation by ensuring env is set
        with patch.dict(os.environ, {"ALETHEIA_SECRET_BACKEND": "env"}, clear=False):
            sm2 = get_secret_manager()
        assert sm1 is not sm2


# ---------------------------------------------------------------------------
# Cloud backend import guards
# ---------------------------------------------------------------------------


class TestCloudBackendImportGuards:
    """Verify cloud backends raise ImportError with a helpful message
    when their SDK is not installed."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_secret_manager()
        yield
        reset_secret_manager()

    def test_vault_requires_hvac(self) -> None:
        with patch.dict("sys.modules", {"hvac": None}):
            from core.secrets.vault import VaultSecretManager

            with pytest.raises(ImportError, match="hvac"):
                VaultSecretManager()

    def test_aws_requires_boto3(self) -> None:
        with patch.dict("sys.modules", {"boto3": None}):
            from core.secrets.aws import AWSSecretManager

            with pytest.raises(ImportError, match="boto3"):
                AWSSecretManager()

    def test_azure_requires_sdk(self) -> None:
        with patch.dict(
            "sys.modules",
            {"azure.identity": None, "azure.keyvault.secrets": None},
        ):
            from core.secrets.azure import AzureSecretManager

            with pytest.raises(ImportError, match="azure"):
                AzureSecretManager()

    def test_gcp_requires_sdk(self) -> None:
        with patch.dict(
            "sys.modules", {"google.cloud": None, "google.cloud.secretmanager": None}
        ):
            from core.secrets.gcp import GCPSecretManager

            with pytest.raises(ImportError, match="google"):
                GCPSecretManager()
