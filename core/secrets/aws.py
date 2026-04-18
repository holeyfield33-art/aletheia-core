"""Aletheia Core — AWS Secrets Manager backend.

Requires ``boto3`` (``pip install aletheia-core[aws]``).

Environment variables
---------------------
AWS_REGION                  AWS region (default ``us-east-1``)
AWS_ACCESS_KEY_ID           Static credentials (CI / dev)
AWS_SECRET_ACCESS_KEY       Static credentials (CI / dev)
ALETHEIA_AWS_SECRET_PREFIX  Prefix for secret names (default ``aletheia/``)

In production, prefer IRSA (IAM Roles for Service Accounts on EKS)
or EC2 instance profiles — boto3 discovers credentials automatically.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.secrets.base import SecretManager

_logger = logging.getLogger("aletheia.secrets.aws")


class AWSSecretManager(SecretManager):
    """AWS Secrets Manager backend."""

    def __init__(self) -> None:
        try:
            import boto3  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "AWS Secrets Manager backend requires 'boto3'. "
                "Install with: pip install aletheia-core[aws]"
            ) from exc

        region = os.environ.get("AWS_REGION", "us-east-1")
        self._prefix = os.environ.get("ALETHEIA_AWS_SECRET_PREFIX", "aletheia/").rstrip("/")
        self._client = boto3.client("secretsmanager", region_name=region)
        _logger.info("AWS Secrets Manager: region=%s prefix=%s", region, self._prefix)

    def _name(self, key: str) -> str:
        return f"{self._prefix}/{key}"

    async def get_secret(self, key: str) -> Optional[str]:
        try:
            resp = self._client.get_secret_value(SecretId=self._name(key))
            return resp.get("SecretString")
        except self._client.exceptions.ResourceNotFoundException:
            return None
        except Exception as exc:
            _logger.debug("AWS get_secret(%s) failed: %s", key, exc)
            return None

    async def set_secret(self, key: str, value: str) -> None:
        name = self._name(key)
        try:
            self._client.put_secret_value(SecretId=name, SecretString=value)
        except self._client.exceptions.ResourceNotFoundException:
            self._client.create_secret(Name=name, SecretString=value)

    async def delete_secret(self, key: str) -> None:
        try:
            self._client.delete_secret(
                SecretId=self._name(key), ForceDeleteWithoutRecovery=True,
            )
        except Exception:
            pass

    async def list_secrets(self, prefix: str = "") -> list[str]:
        try:
            search = f"{self._prefix}/{prefix}" if prefix else self._prefix
            paginator = self._client.get_paginator("list_secrets")
            names: list[str] = []
            for page in paginator.paginate(
                Filters=[{"Key": "name", "Values": [search]}]
            ):
                for s in page.get("SecretList", []):
                    names.append(s["Name"])
            return sorted(names)
        except Exception:
            return []

    async def health_check(self) -> bool:
        try:
            self._client.list_secrets(MaxResults=1)
            return True
        except Exception:
            return False
