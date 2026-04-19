"""Aletheia Core — PostgreSQL decision store (asyncpg).

Production replacement for the SQLite / Upstash decision store.
Provides replay-token claiming and deployment-bundle drift detection,
scoped by ``tenant_id`` for hard multi-tenant isolation.
"""

from __future__ import annotations

import logging
import time

from core.decision_store import ReplayCheckResult
from core.persistence import tenant_scope

_logger = logging.getLogger("aletheia.persistence.pg_decision_store")

_DEFAULT_TTL_SECONDS = 3600
_CURRENT_SCHEMA_VERSION = 1


class PgDecisionStore:
    """Async PostgreSQL decision store with tenant isolation."""

    def __init__(self) -> None:
        self._pool = None
        self._degraded = False

    @property
    def backend(self) -> str:
        return "postgres"

    @property
    def degraded(self) -> bool:
        return self._degraded

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_db(self, pool) -> None:
        self._pool = pool
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _decision_schema_version (
                    id      INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL
                )
            """)
            row = await conn.fetchrow(
                "SELECT version FROM _decision_schema_version WHERE id = 1"
            )
            current = row["version"] if row else 0

            if current < 1:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS decision_tokens (
                        token          TEXT NOT NULL,
                        tenant_id      TEXT NOT NULL DEFAULT 'default',
                        request_id     TEXT NOT NULL,
                        issued_at      BIGINT NOT NULL,
                        expires_at     BIGINT NOT NULL,
                        policy_version TEXT NOT NULL,
                        manifest_hash  TEXT NOT NULL,
                        PRIMARY KEY (token, tenant_id)
                    )
                """)
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_dt_expires ON decision_tokens(expires_at)"
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_dt_tenant ON decision_tokens(tenant_id)"
                )
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS deployment_bundle (
                        id             INTEGER NOT NULL CHECK (id = 1),
                        tenant_id      TEXT NOT NULL DEFAULT 'default',
                        policy_version TEXT NOT NULL,
                        manifest_hash  TEXT NOT NULL,
                        updated_at     BIGINT NOT NULL,
                        PRIMARY KEY (id, tenant_id)
                    )
                """)

            await conn.execute(
                """
                INSERT INTO _decision_schema_version (id, version) VALUES (1, $1)
                ON CONFLICT (id) DO UPDATE SET version = $1
            """,
                _CURRENT_SCHEMA_VERSION,
            )
        _logger.info("PgDecisionStore schema at version %d", _CURRENT_SCHEMA_VERSION)

    # ------------------------------------------------------------------
    # Replay defense — tenant-scoped
    # ------------------------------------------------------------------

    async def claim_token(
        self,
        *,
        token: str,
        request_id: str,
        policy_version: str,
        manifest_hash: str,
        now_ts: int | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        tenant_id: str | None = None,
    ) -> ReplayCheckResult:
        tid = tenant_scope(tenant_id)
        now_ts = now_ts or int(time.time())
        try:
            async with self._pool.acquire() as conn:
                # Prune expired tokens
                await conn.execute(
                    "DELETE FROM decision_tokens WHERE expires_at < $1 AND tenant_id = $2",
                    now_ts,
                    tid,
                )
                # Attempt insert (PK prevents duplicates)
                try:
                    await conn.execute(
                        """INSERT INTO decision_tokens
                           (token, tenant_id, request_id, issued_at, expires_at,
                            policy_version, manifest_hash)
                           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                        token,
                        tid,
                        request_id,
                        now_ts,
                        now_ts + ttl_seconds,
                        policy_version,
                        manifest_hash,
                    )
                except Exception:
                    # Unique constraint violation → replay
                    return ReplayCheckResult(accepted=False, reason="replay_detected")
            self._degraded = False
            return ReplayCheckResult(accepted=True, reason="accepted")
        except Exception as exc:
            _logger.error(
                "PgDecisionStore claim_token error: %s", exc
            )  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            self._degraded = True
            return ReplayCheckResult(
                accepted=False, reason="decision_store_unavailable"
            )

    async def verify_bundle(
        self,
        *,
        policy_version: str,
        manifest_hash: str,
        now_ts: int | None = None,
        tenant_id: str | None = None,
    ) -> ReplayCheckResult:
        tid = tenant_scope(tenant_id)
        now_ts = now_ts or int(time.time())
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT policy_version, manifest_hash FROM deployment_bundle "
                    "WHERE id = 1 AND tenant_id = $1",
                    tid,
                )
                if row is None:
                    await conn.execute(
                        "INSERT INTO deployment_bundle (id, tenant_id, policy_version, "
                        "manifest_hash, updated_at) VALUES (1, $1, $2, $3, $4)",
                        tid,
                        policy_version,
                        manifest_hash,
                        now_ts,
                    )
                    return ReplayCheckResult(accepted=True, reason="bundle_registered")

                if (
                    row["policy_version"] != policy_version
                    or row["manifest_hash"] != manifest_hash
                ):
                    return ReplayCheckResult(
                        accepted=False, reason="partial_deployment_drift"
                    )
                return ReplayCheckResult(accepted=True, reason="bundle_verified")
        except Exception as exc:
            _logger.error("PgDecisionStore verify_bundle error: %s", exc)
            self._degraded = True
            return ReplayCheckResult(
                accepted=False, reason="decision_store_unavailable"
            )
