"""Aletheia Core — HashiCorp Vault secret backend.

Requires the ``hvac`` package (``pip install aletheia-core[vault]``).
Supports Token and AppRole authentication.

Environment variables
---------------------
VAULT_ADDR          Vault server URL (e.g. ``https://vault.internal:8200``)
VAULT_TOKEN         Static token (dev / CI only)
VAULT_ROLE_ID       AppRole role ID (production)
VAULT_SECRET_ID     AppRole secret ID (production)
VAULT_MOUNT_POINT   KV v2 mount (default ``secret``)
VAULT_PATH_PREFIX   Key prefix inside the mount (default ``aletheia/``)
VAULT_NAMESPACE     Vault Enterprise namespace (optional)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.secrets.base import SecretManager

_logger = logging.getLogger("aletheia.secrets.vault")


class VaultSecretManager(SecretManager):
    """HashiCorp Vault KV v2 backend."""

    def __init__(self) -> None:
        try:
            import hvac  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "HashiCorp Vault backend requires the 'hvac' package. "
                "Install with: pip install aletheia-core[vault]"
            ) from exc

        self._addr = os.environ.get("VAULT_ADDR", "")
        if not self._addr:
            raise ValueError("VAULT_ADDR must be set for the Vault secret backend.")

        namespace = os.environ.get("VAULT_NAMESPACE") or None
        self._client = hvac.Client(url=self._addr, namespace=namespace)
        self._mount = os.environ.get("VAULT_MOUNT_POINT", "secret")
        self._prefix = os.environ.get("VAULT_PATH_PREFIX", "aletheia/").rstrip("/")

        # --- Authentication ---
        token = os.environ.get("VAULT_TOKEN", "")
        role_id = os.environ.get("VAULT_ROLE_ID", "")
        secret_id = os.environ.get("VAULT_SECRET_ID", "")

        if token:
            self._client.token = token
            _logger.info("Vault: authenticated with static token")
        elif role_id and secret_id:
            resp = self._client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            self._client.token = resp["auth"]["client_token"]
            _logger.info("Vault: authenticated with AppRole")
        else:
            raise ValueError(
                "Vault backend requires VAULT_TOKEN or "
                "(VAULT_ROLE_ID + VAULT_SECRET_ID)."
            )

    def _path(self, key: str) -> str:
        return f"{self._prefix}/{key.lower()}"

    async def get_secret(self, key: str) -> Optional[str]:
        try:
            resp = self._client.secrets.kv.v2.read_secret_version(
                path=self._path(key),
                mount_point=self._mount,
                raise_on_deleted_version=True,
            )
            return resp["data"]["data"].get("value")
        except Exception as exc:
            _logger.debug(
                "Vault get_secret(%s) failed: %s", key, exc
            )  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            return None

    async def set_secret(self, key: str, value: str) -> None:
        self._client.secrets.kv.v2.create_or_update_secret(
            path=self._path(key),
            secret={"value": value},
            mount_point=self._mount,
        )

    async def delete_secret(self, key: str) -> None:
        try:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=self._path(key),
                mount_point=self._mount,
            )
        except Exception:
            pass  # no-op if missing

    async def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            search_path = f"{self._prefix}/{prefix.lower()}" if prefix else self._prefix
            resp = self._client.secrets.kv.v2.list_secrets(
                path=search_path,
                mount_point=self._mount,
            )
            return sorted(resp["data"]["keys"])
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            return self._client.is_authenticated()
        except Exception:
            return False

    async def close(self) -> None:
        # hvac client doesn't hold persistent connections in default mode.
        pass
