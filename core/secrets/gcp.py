"""Aletheia Core — GCP Secret Manager backend.

Requires ``google-cloud-secret-manager``
(``pip install aletheia-core[gcp]``).

Environment variables
---------------------
GCP_PROJECT_ID                  GCP project (required)
GOOGLE_APPLICATION_CREDENTIALS  Service-account JSON key file (dev)
ALETHEIA_GCP_SECRET_PREFIX      Prefix for secret IDs (default ``aletheia-``)

In production on GKE, prefer Workload Identity — the client library
discovers credentials automatically.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.secrets.base import SecretManager

_logger = logging.getLogger("aletheia.secrets.gcp")


class GCPSecretManager(SecretManager):
    """Google Cloud Secret Manager backend."""

    def __init__(self) -> None:
        try:
            from google.cloud import secretmanager  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "GCP Secret Manager backend requires "
                "'google-cloud-secret-manager'. "
                "Install with: pip install aletheia-core[gcp]"
            ) from exc

        self._project = os.environ.get("GCP_PROJECT_ID", "")
        if not self._project:
            raise ValueError("GCP_PROJECT_ID must be set for the GCP secret backend.")

        self._prefix = os.environ.get("ALETHEIA_GCP_SECRET_PREFIX", "aletheia-")
        self._client = secretmanager.SecretManagerServiceClient()
        self._parent = f"projects/{self._project}"
        _logger.info(
            "GCP Secret Manager: project=%s prefix=%s", self._project, self._prefix
        )  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure

    def _secret_id(self, key: str) -> str:
        """GCP secret IDs: alphanumeric + hyphens + underscores."""
        return f"{self._prefix}{key.lower().replace('/', '-')}"

    def _secret_path(self, key: str) -> str:
        return f"{self._parent}/secrets/{self._secret_id(key)}/versions/latest"

    async def get_secret(self, key: str) -> Optional[str]:
        try:
            resp = self._client.access_secret_version(
                request={"name": self._secret_path(key)}
            )
            return resp.payload.data.decode("utf-8")
        except Exception as exc:
            _logger.debug(
                "GCP get_secret(%s) failed: %s", key, exc
            )  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            return None

    async def set_secret(self, key: str, value: str) -> None:
        sid = self._secret_id(key)
        full_name = f"{self._parent}/secrets/{sid}"
        # Create secret if it doesn't exist, then add version.
        try:
            self._client.get_secret(request={"name": full_name})
        except Exception:
            self._client.create_secret(
                request={
                    "parent": self._parent,
                    "secret_id": sid,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        self._client.add_secret_version(
            request={"parent": full_name, "payload": {"data": value.encode("utf-8")}}
        )

    async def delete_secret(self, key: str) -> None:
        try:
            self._client.delete_secret(
                request={"name": f"{self._parent}/secrets/{self._secret_id(key)}"}
            )
        except Exception:
            pass

    async def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            full_prefix = f"{self._prefix}{prefix.lower()}" if prefix else self._prefix
            names: list[str] = []
            for secret in self._client.list_secrets(request={"parent": self._parent}):
                # secret.name is "projects/X/secrets/Y"
                sid = secret.name.rsplit("/", 1)[-1]
                if sid.startswith(full_prefix):
                    names.append(sid)
            return sorted(names)
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            # List one secret to verify connectivity + auth.
            it = self._client.list_secrets(
                request={"parent": self._parent, "page_size": 1}
            )
            next(iter(it), None)
            return True
        except Exception:
            return False

    async def close(self) -> None:
        try:
            self._client.transport.close()
        except Exception:
            pass
