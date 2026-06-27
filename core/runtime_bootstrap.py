# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Runtime bootstrap helpers extracted from the FastAPI gateway module."""

from __future__ import annotations

import hashlib
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Callable

from core.config import env_bool, settings, upstash_configured
from core.secret_rotation import install_sigusr1_handler


def resolve_demo_api_key() -> tuple[str, str]:
    """Return configured demo key and its environment source."""
    raw_key = os.getenv("ALETHEIA_DEMO_API_KEY", "").strip()
    if raw_key:
        return raw_key, "ALETHEIA_DEMO_API_KEY"

    raw_key = os.getenv("ALETHEIA_API_KEY", "").strip()
    if raw_key:
        return raw_key, "ALETHEIA_API_KEY"

    return "", ""


def demo_key_health_signal(*, key_store: Any) -> dict[str, str | bool]:
    """Report whether configured demo key exists in KeyStore."""
    raw_key, key_source = resolve_demo_api_key()
    if not raw_key:
        return {
            "configured": False,
            "registered": False,
            "status": "not_configured",
            "source": "",
        }

    try:
        registered = key_store.lookup_by_hash(raw_key) is not None
    except Exception:
        return {
            "configured": True,
            "registered": False,
            "status": "lookup_error",
            "source": key_source,
        }

    return {
        "configured": True,
        "registered": registered,
        "status": "registered" if registered else "missing",
        "source": key_source,
    }


def seed_demo_key(*, key_store: Any, logger: Any) -> None:
    """Provision the public demo key into the KeyStore at startup."""
    raw_key, key_source = resolve_demo_api_key()
    if not raw_key:
        return

    try:
        if key_store.lookup_by_hash(raw_key) is not None:
            return
    except Exception as exc:
        logger.warning("demo-key seed: lookup failed (%s); skipping", exc)
        return

    try:
        key_store.import_raw_key(
            name="hosted-demo",
            raw_key=raw_key,
            plan="trial",
            role="operator",
        )
        logger.info("demo-key seed: %s registered in KeyStore", key_source)
    except AttributeError:
        logger.error(
            "demo-key seed: KeyStore.import_raw_key() not available - "
            "create the demo key manually via POST /v1/keys"
        )
    except Exception as exc:
        logger.error("demo-key seed: failed to register demo key (%s)", exc)


async def startup_checks(*, judge_load_policy: Callable[[], None], logger: Any) -> None:
    """Pre-warm model and validate critical runtime secrets."""
    # If ENVIRONMENT=production, refuse shadow mode - deny-decisions must be enforced
    if (
        os.getenv("ENVIRONMENT", "").lower() == "production"
        and settings.mode != "active"
    ):
        logger.critical(
            "FATAL: ENVIRONMENT=production but ALETHEIA_MODE=%s. "
            "Production must run in active mode. "
            "Set ALETHEIA_MODE=active or remove ENVIRONMENT=production. "
            "Refusing to start.",
            settings.mode,
        )
        sys.exit(1)

    receipt_secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "")
    has_ed25519_priv = bool(
        os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY", "").strip()
        or os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", "").strip()
    )

    # Active mode needs SOME signing material — either Ed25519 (preferred) or
    # legacy HMAC secret (still accepted during migration cutover).
    if settings.mode == "active" and not has_ed25519_priv and not receipt_secret:
        logger.critical(
            "FATAL: no receipt signing material configured and mode=active. "
            "Audit receipts would be unsigned (UNSIGNED_DEV_MODE). "
            "Configure ALETHEIA_RECEIPT_PRIVATE_KEY (PEM, Ed25519, preferred) "
            "or ALETHEIA_RECEIPT_PRIVATE_KEY_PATH, or set ALETHEIA_RECEIPT_SECRET "
            "(legacy HMAC) for the migration cutover window, "
            "or switch to mode=shadow for development. Refusing to start."
        )
        sys.exit(1)

    # Strict mode (the v2.0.0 default) requires Ed25519 specifically — without
    # it, build_tmr_receipt() would mint HMAC receipts that verify_receipt_or_raise()
    # then rejects, leaving the service producing receipts it cannot verify.
    if (
        settings.mode == "active"
        and settings.require_ed25519_receipts
        and not has_ed25519_priv
    ):
        logger.critical(
            "FATAL: require_ed25519_receipts=True (the secure default) but no "
            "Ed25519 signing key is configured. The service would mint HMAC "
            "receipts that its own verifier rejects. Configure "
            "ALETHEIA_RECEIPT_PRIVATE_KEY (PEM) or "
            "ALETHEIA_RECEIPT_PRIVATE_KEY_PATH, or set "
            "ALETHEIA_REQUIRE_ED25519_RECEIPTS=false for the migration "
            "cutover window. Refusing to start."
        )
        sys.exit(1)

    min_secret_len = 32
    if receipt_secret and len(receipt_secret) < min_secret_len:
        logger.critical(
            "FATAL: ALETHEIA_RECEIPT_SECRET is too short (%d chars). "
            "Minimum is %d characters. Generate with: openssl rand -hex 32",
            len(receipt_secret),
            min_secret_len,
        )
        sys.exit(1)

    if os.getenv("ALETHEIA_API_KEYS", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            logger.critical(
                "FATAL: ALETHEIA_API_KEYS is set in production. "
                "Environment-based API keys are no longer supported. "
                "Use the KeyStore (POST /v1/keys) to provision keys. "
                "Remove ALETHEIA_API_KEYS to proceed. Refusing to start."
            )
            sys.exit(1)
        logger.warning(
            "ALETHEIA_API_KEYS is set but will be IGNORED. "
            "Environment-based API keys are deprecated. "
            "Use the KeyStore (POST /v1/keys) to provision keys."
        )

    if os.getenv("ENVIRONMENT", "").lower() == "production" and env_bool(
        "ALETHEIA_AUTH_DISABLED"
    ):
        logger.critical(
            "FATAL: ALETHEIA_AUTH_DISABLED=true is not allowed in production. "
            "Configure ALETHEIA_API_KEYS instead. Refusing to start."
        )
        sys.exit(1)

    if not os.getenv("ALETHEIA_ALIAS_SALT", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            logger.critical(
                "FATAL: ALETHEIA_ALIAS_SALT is not set in production. "
                "Daily alias bank rotation is predictable without a salt. "
                "Generate: openssl rand -hex 32. Refusing to start."
            )
            sys.exit(1)
        logger.warning(
            "WARNING: ALETHEIA_ALIAS_SALT is not set. "
            "Daily alias bank rotation is predictable. Set this in production. "
            "Generate: openssl rand -hex 32"
        )

    if not os.getenv("ALETHEIA_KEY_SALT", "").strip():
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            logger.critical(
                "FATAL: ALETHEIA_KEY_SALT is not set in production. "
                "API key hashing is unsalted. "
                "Generate: openssl rand -hex 32. Refusing to start."
            )
            sys.exit(1)

    pinned_hash = os.getenv("ALETHEIA_MANIFEST_HASH", "").strip()
    if pinned_hash:
        try:
            actual_hash = hashlib.sha256(
                Path("manifest/security_policy.json").read_bytes()
            ).hexdigest()
            if not secrets.compare_digest(pinned_hash, actual_hash):
                logger.critical(
                    "FATAL: Manifest hash drift detected. "
                    "Expected %s, got %s. Refusing to start.",
                    pinned_hash[:16] + "...",
                    actual_hash[:16] + "...",
                )
                sys.exit(1)
            logger.info("Manifest hash pinning verified: %s", actual_hash[:16] + "...")
        except FileNotFoundError:
            logger.critical(
                "FATAL: ALETHEIA_MANIFEST_HASH is set but "
                "manifest/security_policy.json is missing. Refusing to start."
            )
            sys.exit(1)
    elif os.getenv("ENVIRONMENT", "").lower() == "production":
        logger.warning(
            "WARNING: ALETHEIA_MANIFEST_HASH is not set in production. "
            "Manifest drift detection is disabled. "
            "Pin the hash: sha256sum manifest/security_policy.json"
        )

    if os.getenv("ENVIRONMENT", "").lower() == "production":
        if settings.database_backend == "postgres":
            if not settings.database_url and not os.getenv("DATABASE_URL", ""):
                logger.critical(
                    "FATAL: database_backend=postgres but DATABASE_URL is not set "
                    "in production. Refusing to start."
                )
                sys.exit(1)
            db_url = settings.database_url or os.getenv("DATABASE_URL", "")
            if "sslmode" not in db_url and "sslmode=require" not in db_url:
                logger.critical(
                    "FATAL: DATABASE_URL missing sslmode=require in production. "
                    "TLS is required. Add ?sslmode=require to your connection string."
                )
                sys.exit(1)
        if not os.getenv("REDIS_URL", "") and not upstash_configured():
            logger.critical(
                "FATAL: Neither REDIS_URL nor UPSTASH_REDIS_REST_URL is set "
                "in production. Redis is required for distributed rate limiting "
                "and replay defense. Refusing to start."
            )
            sys.exit(1)

    install_sigusr1_handler(
        reload_api_keys_fn=None,
        reload_judge_fn=judge_load_policy,
    )
    logger.info("Secret rotation handler installed (kill -SIGUSR1 to rotate)")
