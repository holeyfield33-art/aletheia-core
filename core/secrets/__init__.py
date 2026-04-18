"""Aletheia Core — Pluggable secret-manager layer.

Usage::

    from core.secrets import get_secret_manager

    sm = get_secret_manager()          # singleton, backend from config
    val = await sm.get_secret("RECEIPT_SECRET")

Backend selection (``ALETHEIA_SECRET_BACKEND`` env var):

    env     — os.environ (default, zero-dependency, full backward compat)
    vault   — HashiCorp Vault KV v2  (requires ``hvac``)
    aws     — AWS Secrets Manager    (requires ``boto3``)
    azure   — Azure Key Vault        (requires ``azure-identity``, ``azure-keyvault-secrets``)
    gcp     — GCP Secret Manager     (requires ``google-cloud-secret-manager``)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.secrets.base import SecretManager

_logger = logging.getLogger("aletheia.secrets")

_BACKENDS = {
    "env": "core.secrets.env.EnvSecretManager",
    "vault": "core.secrets.vault.VaultSecretManager",
    "aws": "core.secrets.aws.AWSSecretManager",
    "azure": "core.secrets.azure.AzureSecretManager",
    "gcp": "core.secrets.gcp.GCPSecretManager",
}

_instance: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Return the singleton secret-manager instance.

    The backend is chosen once (first call) based on
    ``ALETHEIA_SECRET_BACKEND`` and cached for the process lifetime.
    """
    global _instance
    if _instance is not None:
        return _instance

    backend_name = os.environ.get("ALETHEIA_SECRET_BACKEND", "env").lower().strip()
    fqn = _BACKENDS.get(backend_name)
    if fqn is None:
        raise ValueError(
            f"Unknown secret backend '{backend_name}'. "
            f"Valid options: {', '.join(sorted(_BACKENDS))}."
        )

    module_path, class_name = fqn.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    _instance = cls()
    _logger.info("Secret manager initialised: backend=%s", backend_name)
    return _instance


def reset_secret_manager() -> None:
    """Reset the singleton (for testing only)."""
    global _instance
    _instance = None


__all__ = ["SecretManager", "get_secret_manager", "reset_secret_manager"]
