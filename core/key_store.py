"""Aletheia Core — API key store with SQLite backend.

Manages API key lifecycle: creation, validation, quota enforcement,
and usage tracking. Keys are hashed with SHA-256 before storage.
Raw keys are returned exactly once at creation time and never persisted.

Default quotas (configurable via env):
  ALETHEIA_TRIAL_QUOTA  — trial plan (default 1000 / month)
    ALETHEIA_PRO_QUOTA    — pro plan   (default 50000 / month)
    ALETHEIA_MAX_QUOTA    — max plan   (default 200000 / month)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.persistence import tenant_scope

_logger = logging.getLogger("aletheia.key_store")

# ---------------------------------------------------------------------------
# Plan defaults — single config source
# ---------------------------------------------------------------------------

DEFAULT_QUOTAS: dict[str, int] = {}
for _plan_name, _default_val in [
    ("trial", "1000"),
    ("pro", "50000"),
    ("max", "200000"),
]:
    _quota = int(os.getenv(f"ALETHEIA_{_plan_name.upper()}_QUOTA", _default_val))
    if _quota <= 0:
        raise ValueError(
            f"ALETHEIA_{_plan_name.upper()}_QUOTA must be positive, got {_quota}"
        )
    DEFAULT_QUOTAS[_plan_name] = _quota

_DB_PATH = os.getenv("ALETHEIA_KEYSTORE_PATH", "data/keys.db")


# Key hashing — uses HMAC-SHA256 with a per-deployment salt.
# If ALETHEIA_KEY_SALT is not set, falls back to plain SHA-256
# (acceptable for dev, logged as a warning at module load time).
_KEY_SALT = os.getenv("ALETHEIA_KEY_SALT", "").encode("utf-8")
if not _KEY_SALT:
    _logger.warning(
        "ALETHEIA_KEY_SALT is not set — API key hashing uses plain SHA-256. "
        "Set ALETHEIA_KEY_SALT for production (generate: openssl rand -hex 32)."
    )


def _hash_key(raw_key: str) -> str:
    """HMAC-SHA256 hash of raw API key for storage (salted when salt is available)."""
    if _KEY_SALT:
        return hmac.new(_KEY_SALT, raw_key.encode("utf-8"), hashlib.sha256).hexdigest()
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class KeyRecord:
    id: str
    name: str
    key_hash: str
    key_prefix: str
    plan: str
    status: str
    monthly_quota: int
    requests_used: int
    period_start: str
    period_end: str
    created_at: str
    last_used_at: Optional[str]
    user_id: str | None = None
    role: str = "operator"  # RBAC role (viewer/auditor/operator/admin)
    tenant_id: str = "default"

    def to_public_dict(self) -> dict:
        """Return a dict safe for API responses (omits key_hash)."""
        d = asdict(self)
        del d["key_hash"]
        return d


@dataclass
class QuotaCheck:
    allowed: bool
    reason: str
    requests_used: int
    monthly_quota: int


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


def _current_period_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return (period_start, period_end) for the month containing *now*."""
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)
    return period_start, period_end


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class KeyStore:
    """SQLite-backed API key store with quota enforcement."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or _DB_PATH
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        # Enforce restrictive permissions on DB file
        db_file = Path(self._db_path)
        db_file.touch(exist_ok=True)
        try:
            os.chmod(self._db_path, 0o600)
        except OSError:
            pass  # best-effort on platforms that don't support chmod
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if mode.lower() != "wal":
            _logger.warning("Failed to enable WAL mode; got %s", mode)
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    _SCHEMA_VERSION = 3  # bump when adding migrations

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                # Schema version tracking
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS _key_schema_version (
                        id      INTEGER PRIMARY KEY CHECK (id = 1),
                        version INTEGER NOT NULL
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id            TEXT PRIMARY KEY,
                        tenant_id     TEXT NOT NULL DEFAULT 'default',
                        name          TEXT NOT NULL,
                        key_hash      TEXT NOT NULL UNIQUE,
                        key_prefix    TEXT NOT NULL,
                        plan          TEXT NOT NULL DEFAULT 'trial',
                        status        TEXT NOT NULL DEFAULT 'active',
                        monthly_quota INTEGER NOT NULL,
                        requests_used INTEGER NOT NULL DEFAULT 0,
                        period_start  TEXT NOT NULL,
                        period_end    TEXT NOT NULL,
                        created_at    TEXT NOT NULL,
                        last_used_at  TEXT,
                        user_id       TEXT,
                        role          TEXT NOT NULL DEFAULT 'operator'
                    )
                """)
                # Migrate existing tables: add user_id column if missing
                try:
                    conn.execute("ALTER TABLE api_keys ADD COLUMN user_id TEXT")
                except sqlite3.OperationalError:
                    pass  # column already exists
                # Migrate existing tables: add role column if missing
                try:
                    conn.execute(
                        "ALTER TABLE api_keys ADD COLUMN role TEXT NOT NULL DEFAULT 'operator'"
                    )
                except sqlite3.OperationalError:
                    pass  # column already exists
                # v3: add tenant_id column + backfill existing rows
                try:
                    conn.execute(
                        "ALTER TABLE api_keys ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                    )
                    # Backfill any NULL rows (safety net)
                    conn.execute(
                        "UPDATE api_keys SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = ''"
                    )
                    _logger.info("Migrated existing keys to tenant_id='default'")
                except sqlite3.OperationalError:
                    pass  # column already exists
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)"
                )
                # Upsert schema version
                conn.execute(
                    "INSERT OR REPLACE INTO _key_schema_version (id, version) VALUES (1, ?)",
                    (self._SCHEMA_VERSION,),
                )
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Key lifecycle
    # ------------------------------------------------------------------

    def create_key(
        self,
        name: str,
        plan: str = "trial",
        user_id: str | None = None,
        role: str = "operator",
        tenant_id: str | None = None,
    ) -> tuple[str, KeyRecord]:
        """Create a new API key.

        Returns ``(raw_key, record)``.  The raw key is returned exactly
        once — only the SHA-256 hash is persisted.
        """
        tid = tenant_scope(tenant_id)
        if role not in ("viewer", "auditor", "operator", "admin"):
            role = "operator"
        if plan not in DEFAULT_QUOTAS:
            plan = "trial"

        raw_key = f"sk_{plan}_" + secrets.token_hex(24)
        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:12] + "..." + raw_key[-4:]
        key_id = secrets.token_hex(8)

        now = datetime.now(timezone.utc)
        period_start, period_end = _current_period_bounds(now)
        quota = DEFAULT_QUOTAS[plan]

        record = KeyRecord(
            id=key_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            plan=plan,
            status="active",
            monthly_quota=quota,
            requests_used=0,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            created_at=now.isoformat(),
            last_used_at=None,
            user_id=user_id,
            role=role,
        )

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO api_keys
                        (id, tenant_id, name, key_hash, key_prefix, plan, status,
                         monthly_quota, requests_used, period_start, period_end,
                         created_at, last_used_at, user_id, role)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.id,
                        tid,
                        record.name,
                        record.key_hash,
                        record.key_prefix,
                        record.plan,
                        record.status,
                        record.monthly_quota,
                        record.requests_used,
                        record.period_start,
                        record.period_end,
                        record.created_at,
                        record.last_used_at,
                        record.user_id,
                        record.role,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        _logger.info("key_created id=%s plan=%s prefix=%s", key_id, plan, key_prefix)
        return raw_key, record

    def import_raw_key(
        self,
        name: str,
        raw_key: str,
        plan: str = "trial",
        user_id: str | None = None,
        role: str = "operator",
        tenant_id: str | None = None,
    ) -> KeyRecord:
        """Register a pre-existing raw key (e.g. injected via env at startup).

        Used by the hosted demo seed path so the public /demo flow survives
        backend restarts even when the KeyStore is on an ephemeral disk. The
        raw key is hashed for storage; the plaintext is never persisted.
        Idempotent — returns the existing record if the key is already known.
        """
        existing = self.lookup_by_hash(raw_key, tenant_id=tenant_id)
        if existing is not None:
            return existing

        tid = tenant_scope(tenant_id)
        if role not in ("viewer", "auditor", "operator", "admin"):
            role = "operator"
        if plan not in DEFAULT_QUOTAS:
            plan = "trial"

        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:12] + "..." + raw_key[-4:]
        key_id = secrets.token_hex(8)
        now = datetime.now(timezone.utc)
        period_start, period_end = _current_period_bounds(now)
        quota = DEFAULT_QUOTAS[plan]

        record = KeyRecord(
            id=key_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            plan=plan,
            status="active",
            monthly_quota=quota,
            requests_used=0,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            created_at=now.isoformat(),
            last_used_at=None,
            user_id=user_id,
            role=role,
        )

        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT INTO api_keys
                        (id, tenant_id, name, key_hash, key_prefix, plan, status,
                         monthly_quota, requests_used, period_start, period_end,
                         created_at, last_used_at, user_id, role)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.id,
                        tid,
                        record.name,
                        record.key_hash,
                        record.key_prefix,
                        record.plan,
                        record.status,
                        record.monthly_quota,
                        record.requests_used,
                        record.period_start,
                        record.period_end,
                        record.created_at,
                        record.last_used_at,
                        record.user_id,
                        record.role,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        _logger.info("key_imported id=%s plan=%s prefix=%s", key_id, plan, key_prefix)
        return record

    def lookup_by_hash(
        self, raw_key: str, *, tenant_id: str | None = None
    ) -> Optional[KeyRecord]:
        """Look up a key record by raw key (hashes it internally)."""
        tid = tenant_scope(tenant_id)
        key_hash = _hash_key(raw_key)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM api_keys WHERE key_hash = ? AND tenant_id = ?",
                    (key_hash, tid),
                ).fetchone()
                return self._row_to_record(row) if row else None
            finally:
                conn.close()

    def get_by_id(
        self, key_id: str, *, tenant_id: str | None = None
    ) -> Optional[KeyRecord]:
        """Get key record by ID (safe — no raw key needed)."""
        tid = tenant_scope(tenant_id)
        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM api_keys WHERE id = ? AND tenant_id = ?",
                    (key_id, tid),
                ).fetchone()
                return self._row_to_record(row) if row else None
            finally:
                conn.close()

    def list_keys(self, *, tenant_id: str | None = None) -> list[KeyRecord]:
        """List all key records (ordered by creation date, newest first)."""
        tid = tenant_scope(tenant_id)
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT * FROM api_keys WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tid,),
                ).fetchall()
                return [self._row_to_record(r) for r in rows]
            finally:
                conn.close()

    def revoke_key(self, key_id: str, *, tenant_id: str | None = None) -> bool:
        """Set key status to ``revoked``.  Returns True if a key was modified."""
        tid = tenant_scope(tenant_id)
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute(
                    "UPDATE api_keys SET status = 'revoked' WHERE id = ? AND tenant_id = ? AND status = 'active'",
                    (key_id, tid),
                )
                conn.commit()
                if cursor.rowcount > 0:
                    _logger.info("key_revoked id=%s", key_id)
                return cursor.rowcount > 0
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Quota enforcement (called on every authenticated request)
    # ------------------------------------------------------------------

    def check_and_increment(
        self, raw_key: str, *, tenant_id: str | None = None
    ) -> QuotaCheck:
        """Validate key, enforce quota, and atomically increment usage.

        Handles billing period reset when the current period has expired.
        Returns ``QuotaCheck`` — the caller should inspect ``.allowed``.
        """
        tid = tenant_scope(tenant_id)
        key_hash = _hash_key(raw_key)
        now = datetime.now(timezone.utc)

        with self._lock:
            conn = self._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM api_keys WHERE key_hash = ? AND tenant_id = ?",
                    (key_hash, tid),
                ).fetchone()

                if not row:
                    return QuotaCheck(
                        allowed=False,
                        reason="Invalid API key.",
                        requests_used=0,
                        monthly_quota=0,
                    )

                record = self._row_to_record(row)

                # Revoked / inactive
                if record.status != "active":
                    return QuotaCheck(
                        allowed=False,
                        reason="API key has been revoked.",
                        requests_used=record.requests_used,
                        monthly_quota=record.monthly_quota,
                    )

                # Billing period reset
                period_end = datetime.fromisoformat(record.period_end)
                if now >= period_end:
                    new_start, new_end = _current_period_bounds(now)
                    conn.execute(
                        """UPDATE api_keys
                           SET requests_used = 0,
                               period_start  = ?,
                               period_end    = ?
                           WHERE key_hash = ? AND tenant_id = ?""",
                        (new_start.isoformat(), new_end.isoformat(), key_hash, tid),
                    )
                    conn.commit()
                    record.requests_used = 0
                    record.period_start = new_start.isoformat()
                    record.period_end = new_end.isoformat()

                # PAYG enterprise keys are fully metered with no hard request cap.
                is_unlimited_payg = record.plan.lower() == "enterprise"

                # Quota check
                if (
                    not is_unlimited_payg
                    and record.requests_used >= record.monthly_quota
                ):
                    return QuotaCheck(
                        allowed=False,
                        reason=(
                            "This API key has reached its monthly request limit. "
                            "Upgrade your hosted plan for higher limits."
                        ),
                        requests_used=record.requests_used,
                        monthly_quota=record.monthly_quota,
                    )

                # Increment
                conn.execute(
                    """UPDATE api_keys
                       SET requests_used = requests_used + 1,
                           last_used_at  = ?
                       WHERE key_hash = ? AND tenant_id = ?""",
                    (now.isoformat(), key_hash, tid),
                )
                conn.commit()

                return QuotaCheck(
                    allowed=True,
                    reason="OK",
                    requests_used=record.requests_used + 1,
                    monthly_quota=record.monthly_quota,
                )
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> KeyRecord:
        # user_id may not exist on older schemas (before migration)
        try:
            uid = row["user_id"]
        except (IndexError, KeyError):
            uid = None
        # role may not exist on older schemas (before migration)
        try:
            role = row["role"]
        except (IndexError, KeyError):
            role = "operator"
        # tenant_id may not exist on older schemas (before v2 migration)
        try:
            tid = row["tenant_id"] or "default"
        except (IndexError, KeyError):
            tid = "default"
        return KeyRecord(
            id=row["id"],
            name=row["name"],
            key_hash=row["key_hash"],
            key_prefix=row["key_prefix"],
            plan=row["plan"],
            status=row["status"],
            monthly_quota=row["monthly_quota"],
            requests_used=row["requests_used"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            created_at=row["created_at"],
            last_used_at=row["last_used_at"],
            user_id=uid,
            role=role,
            tenant_id=tid,
        )

    def list_keys_for_user(
        self, user_id: str, *, tenant_id: str | None = None
    ) -> list[KeyRecord]:
        """List key records belonging to a specific user."""
        tid = tenant_scope(tenant_id)
        with self._lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT * FROM api_keys WHERE user_id = ? AND tenant_id = ? ORDER BY created_at DESC",
                    (user_id, tid),
                ).fetchall()
                return [self._row_to_record(r) for r in rows]
            finally:
                conn.close()

    def reset_for_testing(self) -> None:
        """Drop and recreate the table.  **Tests only.**"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DROP TABLE IF EXISTS api_keys")
                conn.commit()
            finally:
                conn.close()
        self._init_db()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
key_store = KeyStore()
