"""Aletheia Core — PostgreSQL key store (asyncpg).

Production-grade replacement for the SQLite key store.  All queries are
tenant-scoped via the ``tenant_id`` column — the ``tenant_scope()``
helper is called on every public method to enforce hard isolation.

Connection credentials are loaded via the Task-1 SecretManager so that
``DATABASE_URL`` never has to live in plain-text env vars.

Schema version is tracked in a ``_schema_version`` table; migrations
run automatically on ``init_db()``.
"""

from __future__ import annotations

import logging
import secrets as _secrets
from datetime import datetime, timezone
from typing import Any, Optional

from core.key_store import KeyRecord, QuotaCheck, DEFAULT_QUOTAS, _hash_key
from core.persistence import tenant_scope

_logger = logging.getLogger("aletheia.persistence.pg_key_store")

_CURRENT_SCHEMA_VERSION = 2  # bump when adding migrations


class PgKeyStore:
    """Async PostgreSQL key store with hard tenant isolation.

    Usage::

        store = PgKeyStore()
        await store.init_db(pool)  # call once at startup
        raw, record = await store.create_key("my-key", tenant_id="acme")
    """

    def __init__(self) -> None:
        self._pool: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_db(self, pool: Any) -> None:
        """Create tables, indexes, and run idempotent migrations.

        *pool* must be an ``asyncpg.Pool`` instance.
        """
        self._pool = pool
        async with pool.acquire() as conn:
            # Schema version tracking
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _schema_version (
                    id   INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                )
            """)
            row = await conn.fetchrow(
                "SELECT version FROM _schema_version WHERE id = 1"
            )
            current = row["version"] if row else 0

            # v1: base table
            if current < 1:
                await conn.execute("""
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
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status)"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)"
                )

            # v2: tenant isolation index
            if current < 2:
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id)"
                )

            # Upsert schema version
            await conn.execute(
                """
                INSERT INTO _schema_version (id, version) VALUES (1, $1)
                ON CONFLICT (id) DO UPDATE SET version = $1
            """,
                _CURRENT_SCHEMA_VERSION,
            )
        _logger.info("PgKeyStore schema at version %d", _CURRENT_SCHEMA_VERSION)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_record(self, row: Any) -> KeyRecord:
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
            user_id=row["user_id"],
            role=row["role"],
        )

    # ------------------------------------------------------------------
    # Key lifecycle — all tenant-scoped
    # ------------------------------------------------------------------

    async def create_key(
        self,
        name: str,
        plan: str = "trial",
        user_id: str | None = None,
        role: str = "operator",
        tenant_id: str | None = None,
    ) -> tuple[str, KeyRecord]:
        tid = tenant_scope(tenant_id)
        if role not in ("viewer", "auditor", "operator", "admin"):
            role = "operator"
        if plan not in DEFAULT_QUOTAS:
            plan = "trial"

        raw_key = f"sk_{plan}_" + _secrets.token_hex(24)
        key_hash = _hash_key(raw_key)
        key_prefix = raw_key[:12] + "..." + raw_key[-4:]
        key_id = _secrets.token_hex(8)

        now = datetime.now(timezone.utc)
        from core.key_store import _current_period_bounds

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

        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO api_keys
                    (id, tenant_id, name, key_hash, key_prefix, plan, status,
                     monthly_quota, requests_used, period_start, period_end,
                     created_at, last_used_at, user_id, role)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
                key_id,
                tid,
                name,
                key_hash,
                key_prefix,
                plan,
                "active",
                quota,
                0,
                period_start.isoformat(),
                period_end.isoformat(),
                now.isoformat(),
                None,
                user_id,
                role,
            )
        _logger.info("pg key_created id=%s tenant=%s plan=%s", key_id, tid, plan)
        return raw_key, record

    async def lookup_by_hash(
        self,
        raw_key: str,
        *,
        tenant_id: str | None = None,
    ) -> Optional[KeyRecord]:
        tid = tenant_scope(tenant_id)
        key_hash = _hash_key(raw_key)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key_hash = $1 AND tenant_id = $2",
                key_hash,
                tid,
            )
        return self._row_to_record(row) if row else None

    async def get_by_id(
        self,
        key_id: str,
        *,
        tenant_id: str | None = None,
    ) -> Optional[KeyRecord]:
        tid = tenant_scope(tenant_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE id = $1 AND tenant_id = $2",
                key_id,
                tid,
            )
        return self._row_to_record(row) if row else None

    async def list_keys(self, *, tenant_id: str | None = None) -> list[KeyRecord]:
        tid = tenant_scope(tenant_id)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM api_keys WHERE tenant_id = $1 ORDER BY created_at DESC",
                tid,
            )
        return [self._row_to_record(r) for r in rows]

    async def revoke_key(
        self,
        key_id: str,
        *,
        tenant_id: str | None = None,
    ) -> bool:
        tid = tenant_scope(tenant_id)
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE api_keys SET status = 'revoked' "
                "WHERE id = $1 AND tenant_id = $2 AND status = 'active'",
                key_id,
                tid,
            )
        changed = bool(result.split()[-1] != "0")
        if changed:
            _logger.info("pg key_revoked id=%s tenant=%s", key_id, tid)
        return changed

    async def check_and_increment(
        self,
        raw_key: str,
        *,
        tenant_id: str | None = None,
    ) -> QuotaCheck:
        tid = tenant_scope(tenant_id)
        key_hash = _hash_key(raw_key)
        now = datetime.now(timezone.utc)

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM api_keys WHERE key_hash = $1 AND tenant_id = $2",
                key_hash,
                tid,
            )
            if not row:
                return QuotaCheck(
                    allowed=False,
                    reason="Invalid API key.",
                    requests_used=0,
                    monthly_quota=0,
                )
            record = self._row_to_record(row)

            if record.status != "active":
                return QuotaCheck(
                    allowed=False,
                    reason="API key has been revoked.",
                    requests_used=record.requests_used,
                    monthly_quota=record.monthly_quota,
                )

            period_end = datetime.fromisoformat(record.period_end)
            if now >= period_end:
                from core.key_store import _current_period_bounds

                new_start, new_end = _current_period_bounds(now)
                await conn.execute(
                    "UPDATE api_keys SET requests_used = 0, period_start = $1, period_end = $2 "
                    "WHERE key_hash = $3 AND tenant_id = $4",
                    new_start.isoformat(),
                    new_end.isoformat(),
                    key_hash,
                    tid,
                )
                record.requests_used = 0

            is_unlimited_payg = record.plan.lower() == "enterprise"

            if not is_unlimited_payg and record.requests_used >= record.monthly_quota:
                return QuotaCheck(
                    allowed=False,
                    reason="This API key has reached its monthly request limit. "
                    "Upgrade your hosted plan for higher limits.",
                    requests_used=record.requests_used,
                    monthly_quota=record.monthly_quota,
                )

            await conn.execute(
                "UPDATE api_keys SET requests_used = requests_used + 1, last_used_at = $1 "
                "WHERE key_hash = $2 AND tenant_id = $3",
                now.isoformat(),
                key_hash,
                tid,
            )
            return QuotaCheck(
                allowed=True,
                reason="OK",
                requests_used=record.requests_used + 1,
                monthly_quota=record.monthly_quota,
            )

    async def list_keys_for_user(
        self,
        user_id: str,
        *,
        tenant_id: str | None = None,
    ) -> list[KeyRecord]:
        tid = tenant_scope(tenant_id)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM api_keys WHERE user_id = $1 AND tenant_id = $2 "
                "ORDER BY created_at DESC",
                user_id,
                tid,
            )
        return [self._row_to_record(r) for r in rows]
