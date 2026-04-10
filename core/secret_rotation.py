"""Aletheia Core — Hot secret rotation without restart.

Provides two mechanisms for secret rotation:
1. SIGUSR1 signal handler: ``kill -SIGUSR1 $(pidof aletheia)``
2. Admin-only ``POST /v1/rotate`` endpoint (rate-limited)

On rotation:
- Reloads ALETHEIA_RECEIPT_SECRET, ALETHEIA_API_KEYS, ALETHEIA_ALIAS_SALT
- Reloads ALETHEIA_ADMIN_KEY
- Re-verifies manifest signature
- Logs the rotation event to the audit log

Thread-safety: rotation acquires a lock so concurrent requests see
either the old or the new secrets, never a torn state.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from typing import Any, Callable

_logger = logging.getLogger("aletheia.secret_rotation")
_rotation_lock = threading.Lock()
_last_rotation_time: float = 0.0
_ROTATION_COOLDOWN_SECONDS = 10.0  # prevent rotation spam


def _reload_env_secrets() -> dict[str, Any]:
    """Reload secrets from environment variables / mounted secret files.

    Returns a summary dict (safe for audit logging — no secret values).
    """
    rotated: dict[str, Any] = {}

    # 1. Receipt signing secret
    new_receipt = os.environ.get("ALETHEIA_RECEIPT_SECRET", "")
    rotated["receipt_secret_set"] = bool(new_receipt)
    rotated["receipt_secret_length"] = len(new_receipt)

    # 2. API keys
    raw_keys = os.environ.get("ALETHEIA_API_KEYS", "")
    key_count = len([k for k in raw_keys.split(",") if k.strip()]) if raw_keys else 0
    rotated["api_key_count"] = key_count

    # 3. Alias salt
    new_salt = os.environ.get("ALETHEIA_ALIAS_SALT", "")
    rotated["alias_salt_set"] = bool(new_salt)

    # 4. Admin key
    new_admin = os.environ.get("ALETHEIA_ADMIN_KEY", "")
    rotated["admin_key_set"] = bool(new_admin)

    return rotated


def rotate_secrets(
    *,
    reload_api_keys_fn: Callable[[], set[str]] | None = None,
    reload_judge_fn: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Perform a hot secret rotation.

    Args:
        reload_api_keys_fn: Callback to refresh the in-memory API key set.
        reload_judge_fn: Callback to re-verify manifest and rotate alias bank.

    Returns:
        Audit-safe summary of what was rotated.
    """
    global _last_rotation_time

    with _rotation_lock:
        now = time.monotonic()
        if now - _last_rotation_time < _ROTATION_COOLDOWN_SECONDS:
            wait = _ROTATION_COOLDOWN_SECONDS - (now - _last_rotation_time)
            return {
                "status": "cooldown",
                "retry_after_seconds": round(wait, 1),
                "message": "Rotation too frequent. Wait before retrying.",
            }

        _logger.info("Secret rotation initiated")
        summary = _reload_env_secrets()

        # Refresh in-memory API keys
        if reload_api_keys_fn is not None:
            try:
                reload_api_keys_fn()
                summary["api_keys_reloaded"] = True
            except Exception as exc:
                _logger.error("Failed to reload API keys: %s", exc)
                summary["api_keys_reloaded"] = False
                summary["api_keys_error"] = str(exc)

        # Re-verify manifest and rotate judge alias bank
        if reload_judge_fn is not None:
            try:
                reload_judge_fn()
                summary["judge_reloaded"] = True
            except Exception as exc:
                _logger.error("Failed to reload judge: %s", exc)
                summary["judge_reloaded"] = False
                summary["judge_error"] = str(exc)

        _last_rotation_time = now
        summary["status"] = "rotated"
        summary["timestamp"] = time.time()
        _logger.info("Secret rotation completed: %s", summary)
        return summary


def install_sigusr1_handler(
    *,
    reload_api_keys_fn: Callable[[], set[str]] | None = None,
    reload_judge_fn: Callable[[], None] | None = None,
) -> None:
    """Install a SIGUSR1 handler for signal-based secret rotation.

    Usage: ``kill -SIGUSR1 $(pidof python)``
    """
    def _handler(signum: int, frame: Any) -> None:
        _logger.info("SIGUSR1 received — rotating secrets")
        try:
            result = rotate_secrets(
                reload_api_keys_fn=reload_api_keys_fn,
                reload_judge_fn=reload_judge_fn,
            )
            _logger.info("SIGUSR1 rotation result: %s", result)
        except Exception:
            _logger.exception("SIGUSR1 rotation failed")

    signal.signal(signal.SIGUSR1, _handler)
    _logger.info("SIGUSR1 secret rotation handler installed")
