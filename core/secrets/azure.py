# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Azure Key Vault secret backend.

Requires ``azure-identity`` and ``azure-keyvault-secrets``
(``pip install aletheia-core[azure]``).

Environment variables
---------------------
AZURE_VAULT_URL             Key Vault URL (e.g. ``https://myvault.vault.azure.net``)
AZURE_TENANT_ID             Azure AD tenant (for service-principal auth)
AZURE_CLIENT_ID             Service-principal client ID
AZURE_CLIENT_SECRET         Service-principal secret

In production on AKS, prefer Workload Identity — ``DefaultAzureCredential``
discovers it automatically.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.secrets.base import SecretManager

_logger = logging.getLogger("aletheia.secrets.azure")


class AzureSecretManager(SecretManager):
    """Azure Key Vault backend."""

    def __init__(self) -> None:
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore[import-untyped]
            from azure.keyvault.secrets import SecretClient  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "Azure Key Vault backend requires 'azure-identity' and "
                "'azure-keyvault-secrets'. "
                "Install with: pip install aletheia-core[azure]"
            ) from exc

        vault_url = os.environ.get("AZURE_VAULT_URL", "")
        if not vault_url:
            raise ValueError(
                "AZURE_VAULT_URL must be set for the Azure secret backend."
            )

        credential = DefaultAzureCredential()
        self._client = SecretClient(vault_url=vault_url, credential=credential)
        self._credential = credential
        _logger.info("Azure Key Vault: url=%s", vault_url)

    @staticmethod
    def _sanitise_name(key: str) -> str:
        """Azure Key Vault names allow only alphanumeric and hyphens."""
        return key.replace("_", "-").replace("/", "-").lower()

    async def get_secret(self, key: str) -> Optional[str]:
        try:
            secret = self._client.get_secret(self._sanitise_name(key))
            return secret.value
        except Exception as exc:
            _logger.debug(  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
                "Azure get_secret(%s) failed: %s", key, exc
            )
            return None

    async def set_secret(self, key: str, value: str) -> None:
        self._client.set_secret(self._sanitise_name(key), value)

    async def delete_secret(self, key: str) -> None:
        try:
            poller = self._client.begin_delete_secret(self._sanitise_name(key))
            poller.result()
        except Exception:
            pass

    async def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            sanitised_prefix = self._sanitise_name(prefix) if prefix else ""
            props = self._client.list_properties_of_secrets()
            names = [
                p.name for p in props if p.name and p.name.startswith(sanitised_prefix)
            ]
            return sorted(names)
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            # List one secret to verify connectivity.
            next(iter(self._client.list_properties_of_secrets()), None)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        try:
            self._client.close()
            self._credential.close()
        except Exception:
            pass
