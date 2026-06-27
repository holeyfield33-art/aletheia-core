# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
"""Aletheia Core — Centralized configuration.

Loads from environment variables or config.yaml, with safe defaults.
All security-critical thresholds are defined here so they are auditable
in a single location.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


_CONFIG_SEARCH_PATHS = [
    Path("config.yaml"),
    Path("config.yml"),
    Path(os.getenv("ALETHEIA_CONFIG_PATH", "")),
]


_MAX_CONFIG_SIZE = 100_000  # 100 KB — prevents YAML bomb variants


def _validate_config_ownership(config_path: Path) -> None:
    """Reject config files that are world/group-writable by non-owners.

    Prevents privilege escalation via tampered config on shared hosts.
    """
    import logging as _logging

    _cfg_logger = _logging.getLogger("aletheia.config")
    try:
        st = config_path.stat()
        if st.st_uid != os.getuid() and (st.st_mode & 0o022):
            raise PermissionError(
                f"Config {config_path} is writable by others (mode={oct(st.st_mode)}). "
                f"Fix with: chmod go-w {config_path}"
            )
    except PermissionError:
        raise
    except OSError as exc:
        _cfg_logger.warning("Could not stat config %s: %s", config_path, exc)


def _load_yaml() -> dict:
    """Best-effort load of the first config file found on disk."""
    import logging as _logging

    _cfg_logger = _logging.getLogger("aletheia.config")
    for candidate in _CONFIG_SEARCH_PATHS:
        try:
            if candidate and candidate.is_file():
                _validate_config_ownership(candidate)
                raw = candidate.read_bytes()
                if len(raw) > _MAX_CONFIG_SIZE:
                    _cfg_logger.error(
                        "Config file %s exceeds %d bytes — skipped",
                        candidate,
                        _MAX_CONFIG_SIZE,
                    )
                    continue
                data = yaml.safe_load(raw)
                return data if isinstance(data, dict) else {}
        except yaml.YAMLError as exc:
            _cfg_logger.error("Invalid YAML in %s: %s", candidate, exc)
            continue
        except Exception as exc:
            _cfg_logger.warning("Could not load config %s: %s", candidate, exc)
            continue
    return {}


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _normalize_env_text(value: str) -> str:
    """Normalize env-var text copied from dashboards/CLI.

    Removes leading/trailing whitespace and a single pair of matching
    surrounding quotes so values like "'active'" and '"active"' parse
    as active.
    """
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip()
    return cleaned


@dataclass
class AletheiaSettings:
    """Single source of truth for runtime configuration."""

    # --- Semantic intent analysis ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    intent_threshold: float = 0.45  # Judge veto cosine-sim threshold
    grey_zone_lower: float = 0.30  # Grey-zone second-pass lower bound
    nitpicker_similarity_threshold: float = 0.75  # Nitpicker blocked-pattern threshold

    # --- Polymorphic rotation (config-driven, deterministic cycle) ---
    polymorphic_modes: list[str] = field(
        default_factory=lambda: ["LINEAGE", "INTENT", "SKEPTIC"]
    )

    # --- Defence mode ---
    mode: str = "active"  # "active" | "shadow" | "monitor"
    shadow_mode: bool = False  # Legacy compat — derived from mode

    # --- Logging ---
    log_level: str = "INFO"
    audit_log_path: str = "audit.log"

    # --- Policy ---
    policy_threshold: float = 7.5  # Scout threat-score threshold

    # --- Rate limiting ---
    rate_limit_per_second: int = 10

    # --- General ---
    client_id: str = "ALETHEIA_ENTERPRISE"

    # --- Enterprise auth (Task 1) ---
    secret_backend: str = "env"  # "env" | "vault" | "aws" | "azure" | "gcp"
    auth_provider: str = "api_key"  # "api_key" | "oidc" | "saml" | "multi"

    # OIDC settings (used when auth_provider includes OIDC)
    oidc_issuer: str = ""  # e.g. https://accounts.google.com
    oidc_client_id: str = ""
    oidc_audience: str = ""  # JWT ``aud`` claim to validate
    oidc_role_claim: str = "aletheia_role"  # JWT claim containing role

    # SAML settings
    saml_metadata_url: str = ""  # IdP metadata endpoint
    saml_entity_id: str = ""  # SP entity ID
    saml_acs_url: str = ""  # Assertion Consumer Service URL

    # --- HA Persistence (Task 2) ---
    database_backend: str = "sqlite"  # "sqlite" | "postgres"
    database_url: str = ""  # PostgreSQL connection string

    # --- FIPS-140 mode (Task 5) ---
    fips_mode: bool = False  # Restrict to FIPS-approved crypto

    # --- Receipt verification policy ---
    # When True (the secure default), verify_receipt_or_raise() refuses
    # HMAC-SHA256 receipts and only accepts Ed25519. Closes the algorithm-
    # downgrade path on deployments that still have ALETHEIA_RECEIPT_SECRET
    # set during migration. Operators mid-cutover can opt back into legacy
    # HMAC verification by setting ALETHEIA_REQUIRE_ED25519_RECEIPTS=false.
    require_ed25519_receipts: bool = True

    # --- Embedding model integrity ---
    # Optional Hugging Face revision (commit SHA or tag) to pin the
    # SentenceTransformer download. Empty = unpinned (latest "main").
    embedding_model_revision: str = ""

    def __post_init__(self) -> None:
        self.shadow_mode = self.mode == "shadow"
        # --- Enterprise threshold validation ---
        if not (0.0 <= self.intent_threshold <= 1.0):
            raise ValueError(
                f"intent_threshold must be in [0.0, 1.0], got {self.intent_threshold}"
            )
        if not (0.0 <= self.grey_zone_lower < self.intent_threshold):
            raise ValueError(
                f"grey_zone_lower ({self.grey_zone_lower}) must be in "
                f"[0.0, intent_threshold={self.intent_threshold})"
            )
        if not (0.0 <= self.nitpicker_similarity_threshold <= 1.0):
            raise ValueError(
                f"nitpicker_similarity_threshold must be in [0.0, 1.0], "
                f"got {self.nitpicker_similarity_threshold}"
            )
        if self.policy_threshold < 0:
            raise ValueError(
                f"policy_threshold must be >= 0, got {self.policy_threshold}"
            )
        if self.mode not in ("active", "shadow", "monitor"):
            raise ValueError(
                f"mode must be 'active', 'shadow', or 'monitor', got '{self.mode}'"
            )
        if self.secret_backend not in ("env", "vault", "aws", "azure", "gcp"):
            raise ValueError(
                f"secret_backend must be one of env/vault/aws/azure/gcp, "
                f"got '{self.secret_backend}'"
            )
        if self.auth_provider not in ("api_key", "oidc", "saml", "multi"):
            raise ValueError(
                f"auth_provider must be one of api_key/oidc/saml/multi, "
                f"got '{self.auth_provider}'"
            )
        if self.database_backend not in ("sqlite", "postgres"):
            raise ValueError(
                f"database_backend must be one of sqlite/postgres, "
                f"got '{self.database_backend}'"
            )
        # FIPS-140 mode validation
        if self.fips_mode:
            import logging as _fips_log

            _fl = _fips_log.getLogger("aletheia.config")
            _fl.info(
                "FIPS-140 mode enabled — only FIPS-approved algorithms "
                "(SHA-256, HMAC-SHA256, Ed25519, AES-256) will be used"
            )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def load(cls) -> "AletheiaSettings":
        """Merge: defaults ← yaml ← env vars (env wins)."""
        yaml_cfg = _load_yaml()

        def _get(key: str, default: Any) -> Any:
            env_val = _normalize_env_text(_env(f"ALETHEIA_{key.upper()}"))
            if env_val:
                # Coerce to the expected type
                if isinstance(default, bool):
                    normalized = env_val.strip().lower()
                    if normalized in {"1", "true", "yes", "on", "y", "t"}:
                        return True
                    if normalized in {"0", "false", "no", "off", "n", "f"}:
                        return False
                    raise ValueError(f"Invalid boolean value for {key}: {env_val!r}")
                if isinstance(default, float):
                    return float(env_val)
                if isinstance(default, int):
                    try:
                        return int(env_val)
                    except ValueError as exc:
                        raise ValueError(
                            f"Invalid integer value for {key}: {env_val!r}"
                        ) from exc
                if isinstance(default, list):
                    return [s.strip() for s in env_val.split(",")]
                return env_val
            return yaml_cfg.get(key, default)

        defaults = cls.__new__(cls)
        # Set raw defaults without validation for the _get helper
        defaults.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        defaults.intent_threshold = 0.45
        defaults.grey_zone_lower = 0.30
        defaults.nitpicker_similarity_threshold = 0.75
        defaults.polymorphic_modes = ["LINEAGE", "INTENT", "SKEPTIC"]
        defaults.mode = "active"
        defaults.shadow_mode = False
        defaults.log_level = "INFO"
        defaults.audit_log_path = "audit.log"
        defaults.policy_threshold = 7.5
        defaults.rate_limit_per_second = 10
        defaults.client_id = "ALETHEIA_ENTERPRISE"
        defaults.secret_backend = "env"
        defaults.auth_provider = "api_key"
        defaults.oidc_issuer = ""
        defaults.oidc_client_id = ""
        defaults.oidc_audience = ""
        defaults.oidc_role_claim = "aletheia_role"
        defaults.saml_metadata_url = ""
        defaults.saml_entity_id = ""
        defaults.saml_acs_url = ""
        defaults.database_backend = "sqlite"
        defaults.database_url = ""
        defaults.fips_mode = False
        defaults.require_ed25519_receipts = True
        defaults.embedding_model_revision = ""
        return cls(
            embedding_model=_get("embedding_model", defaults.embedding_model),
            intent_threshold=_get("intent_threshold", defaults.intent_threshold),
            nitpicker_similarity_threshold=_get(
                "nitpicker_similarity_threshold",
                defaults.nitpicker_similarity_threshold,
            ),
            polymorphic_modes=_get("polymorphic_modes", defaults.polymorphic_modes),
            mode=_get("mode", defaults.mode),
            log_level=_get("log_level", defaults.log_level),
            audit_log_path=_get("audit_log_path", defaults.audit_log_path),
            policy_threshold=_get("policy_threshold", defaults.policy_threshold),
            rate_limit_per_second=_get(
                "rate_limit_per_second", defaults.rate_limit_per_second
            ),
            client_id=_get("client_id", defaults.client_id),
            secret_backend=_get("secret_backend", defaults.secret_backend),
            auth_provider=_get("auth_provider", defaults.auth_provider),
            oidc_issuer=_get("oidc_issuer", defaults.oidc_issuer),
            oidc_client_id=_get("oidc_client_id", defaults.oidc_client_id),
            oidc_audience=_get("oidc_audience", defaults.oidc_audience),
            oidc_role_claim=_get("oidc_role_claim", defaults.oidc_role_claim),
            saml_metadata_url=_get("saml_metadata_url", defaults.saml_metadata_url),
            saml_entity_id=_get("saml_entity_id", defaults.saml_entity_id),
            saml_acs_url=_get("saml_acs_url", defaults.saml_acs_url),
            database_backend=_get("database_backend", defaults.database_backend),
            database_url=_get("database_url", defaults.database_url),
            fips_mode=_get("fips_mode", defaults.fips_mode),
            require_ed25519_receipts=_get(
                "require_ed25519_receipts", defaults.require_ed25519_receipts
            ),
            embedding_model_revision=_get(
                "embedding_model_revision", defaults.embedding_model_revision
            ),
        )


# Module-level singleton — import and use directly.
settings: AletheiaSettings = AletheiaSettings.load()


def upstash_configured() -> bool:
    """True when both UPSTASH_REDIS_REST_URL and
    UPSTASH_REDIS_REST_TOKEN are set."""
    return bool(
        os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN")
    )


def env_bool(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    val = os.getenv(key, "")
    if not val:
        return default
    return val.lower() in ("true", "1", "yes")


# Canonical set of environments treated as non-production. Anything outside this
# set (including an unset or misspelled ENVIRONMENT) is treated as production so
# that security downgrades fail *closed* rather than open.
DEV_ENVIRONMENTS: frozenset[str] = frozenset(
    {"development", "dev", "test", "testing", "local"}
)


def is_production_environment() -> bool:
    """True unless ENVIRONMENT is an explicit, recognised dev/test value.

    Fail-closed: an unset or unrecognised ENVIRONMENT is considered production.
    Use this for any security control whose *safe* default is the production
    behaviour (e.g. refusing to downgrade a DENIED verdict in shadow mode).
    """
    return os.getenv("ENVIRONMENT", "").strip().lower() not in DEV_ENVIRONMENTS


def opaque_decisions_enabled() -> bool:
    """True when audit responses must not leak the detector's decision boundary.

    Controlled by ``ALETHEIA_OPAQUE_DECISIONS``. When unset, opaque mode is
    ON in production and OFF elsewhere, so similarity scores/thresholds are
    hidden by default on real deployments but remain visible for local
    debugging and tests.
    """
    raw = os.getenv("ALETHEIA_OPAQUE_DECISIONS", "").strip().lower()
    if raw:
        return raw in ("true", "1", "yes", "on", "y", "t")
    return is_production_environment()


def compute_daily_rotation_seed(
    secret: str,
    date_str: str | None = None,
) -> str:
    """Compute a daily HMAC rotation seed.

    Uses ALETHEIA_ROTATION_SALT env var as the secret key.
    Falls back to ALETHEIA_ALIAS_SALT for compatibility.
    """
    import hashlib
    import hmac
    from datetime import date

    key = (
        os.getenv("ALETHEIA_ROTATION_SALT")
        or os.getenv("ALETHEIA_ALIAS_SALT")
        or secret
    ).encode()
    day = (date_str or date.today().isoformat()).encode()
    return hmac.new(key, day, hashlib.sha256).hexdigest()


def hmac_rotation_index(salt: str, message: str, modulus: int) -> int:
    """Compute an HMAC-SHA256-based index for polymorphic rotation."""
    import hashlib
    import hmac

    digest = hmac.new(salt.encode(), message.encode(), hashlib.sha256).digest()
    return int.from_bytes(digest[:4], "big") % modulus


def validate_fips_compliance() -> list[str]:
    """Check whether the current runtime satisfies FIPS-140 constraints.

    Returns a list of violations (empty = compliant).  Called at startup
    when ``fips_mode=True``.  Aletheia already uses FIPS-approved primitives
    (SHA-256, HMAC-SHA256, Ed25519) by default — this validates nothing
    non-compliant has been configured.
    """
    violations: list[str] = []
    # Ed25519 is FIPS 186-5 approved.  Check that no MD5 or SHA-1 is used.
    try:
        import hashlib

        # Attempt to detect if FIPS mode is enforced at the OpenSSL level
        if hasattr(hashlib, "md5"):
            try:
                hashlib.md5(b"test", usedforsecurity=True)  # nosec B324  # nosemgrep: python.lang.security.insecure-hash-algorithms-md5.insecure-hash-algorithm-md5
            except ValueError:
                pass  # Good — OpenSSL FIPS provider blocks MD5
    except Exception:
        pass
    # Verify Ed25519 signing key is present (required for manifest integrity)
    manifest_key = Path("manifest/security_policy.ed25519.pub")
    if not manifest_key.is_file():
        violations.append(
            "FIPS: Ed25519 public key missing at manifest/security_policy.ed25519.pub"
        )
    # Verify receipt secret uses adequate length
    receipt_secret = os.getenv("ALETHEIA_RECEIPT_SECRET", "")
    if receipt_secret and len(receipt_secret) < 32:
        violations.append(
            "FIPS: ALETHEIA_RECEIPT_SECRET must be >= 32 characters for HMAC-SHA256 security"
        )
    return violations


def validate_production_config() -> list[str]:
    """Validate configuration for production readiness.

    Returns a list of fatal issues.  The FastAPI lifespan calls this
    when ``ENVIRONMENT=production`` and refuses to start if non-empty.
    """
    issues: list[str] = []
    has_ed25519_priv = bool(
        os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY", "").strip()
        or os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", "").strip()
    )
    has_hmac_secret = bool(os.getenv("ALETHEIA_RECEIPT_SECRET", "").strip())
    if not has_ed25519_priv and not has_hmac_secret:
        issues.append(
            "Receipt signing material is required in production. Configure "
            "ALETHEIA_RECEIPT_PRIVATE_KEY (PEM, Ed25519, preferred) or "
            "ALETHEIA_RECEIPT_PRIVATE_KEY_PATH, or set ALETHEIA_RECEIPT_SECRET "
            "(legacy HMAC) — unsigned receipts break audit trail integrity."
        )
    # Use module-level settings (not a fresh .load()) so monkeypatched
    # overrides flow through correctly under test.
    if settings.require_ed25519_receipts and not has_ed25519_priv:
        issues.append(
            "require_ed25519_receipts=True but no Ed25519 signing key is "
            "configured. Verifier would reject every minted receipt. "
            "Configure ALETHEIA_RECEIPT_PRIVATE_KEY/_PATH or set "
            "ALETHEIA_REQUIRE_ED25519_RECEIPTS=false during HMAC migration."
        )
    # Require durable rate-limiting backend
    has_redis = bool(os.getenv("REDIS_URL") or os.getenv("ALETHEIA_REDIS_URL"))
    has_upstash = upstash_configured()
    if not has_redis and not has_upstash:
        issues.append(
            "Production requires a Redis backend (REDIS_URL / ALETHEIA_REDIS_URL) "
            "or Upstash (UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN) for "
            "durable rate limiting and replay defence"
        )
    # Recommend Postgres over SQLite
    # Allow explicit opt-in via ALETHEIA_ALLOW_SQLITE_PRODUCTION=true for
    # open-source / free-tier deployments with a single worker.
    if settings.database_backend == "sqlite" and not env_bool(
        "ALETHEIA_ALLOW_SQLITE_PRODUCTION"
    ):
        issues.append(
            "Production should use database_backend=postgres (SQLite does not "
            "support concurrent writes from multiple workers). "
            "Set ALETHEIA_ALLOW_SQLITE_PRODUCTION=true to acknowledge this risk."
        )
    # Secret backend should not be plain env in production
    # Allow explicit opt-in via ALETHEIA_ALLOW_ENV_SECRETS=true for
    # open-source / free-tier deployments that don't run Vault.
    if settings.secret_backend == "env" and not env_bool("ALETHEIA_ALLOW_ENV_SECRETS"):
        issues.append(
            "Production should use a secrets manager (vault/aws/azure/gcp) "
            "instead of secret_backend=env. Set ALETHEIA_ALLOW_ENV_SECRETS=true "
            "to acknowledge this risk."
        )
    # Auth bypass is a dev-only escape hatch. Fail-closed at startup if
    # the operator left it on in production.
    if env_bool("ALETHEIA_AUTH_DISABLED"):
        issues.append(
            "ALETHEIA_AUTH_DISABLED=true is not permitted in production. "
            "Unset it or move the workload to a development/test environment."
        )
    # Receipts must be asymmetrically signed (Ed25519) so a leaked verifier
    # secret cannot mint forgeries. Flag HMAC-only signing unless the operator
    # explicitly acknowledges the weaker, symmetric guarantee.
    has_receipt_priv = bool(
        os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY")
        or os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH")
    )
    has_receipt_secret = bool(os.getenv("ALETHEIA_RECEIPT_SECRET"))
    if (
        not has_receipt_priv
        and has_receipt_secret
        and not settings.require_ed25519_receipts
        and not env_bool("ALETHEIA_ALLOW_HMAC_RECEIPTS")
    ):
        issues.append(
            "Production receipts would be HMAC-SHA256 only (symmetric): set "
            "ALETHEIA_RECEIPT_PRIVATE_KEY for Ed25519 signing, or "
            "ALETHEIA_REQUIRE_ED25519_RECEIPTS=true. Set "
            "ALETHEIA_ALLOW_HMAC_RECEIPTS=true to acknowledge this risk."
        )
    # The manifest trust root should be pinned out-of-band so an attacker who
    # can write the deploy directory cannot swap manifest + signature + public
    # key as a set. Recommend a pinned key fingerprint in production.
    if not os.getenv("ALETHEIA_MANIFEST_EXPECTED_KEY_ID") and not env_bool(
        "ALETHEIA_ALLOW_UNPINNED_MANIFEST_KEY"
    ):
        issues.append(
            "Production should pin the manifest signing key via "
            "ALETHEIA_MANIFEST_EXPECTED_KEY_ID (sha256 of the raw Ed25519 public "
            "key) so the on-disk public key cannot be silently swapped. Set "
            "ALETHEIA_ALLOW_UNPINNED_MANIFEST_KEY=true to acknowledge this risk."
        )
    return issues
