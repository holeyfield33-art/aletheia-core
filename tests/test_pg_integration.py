"""Integration test: PostgreSQL backend via testcontainers.

Requires: ``pip install testcontainers[postgres] asyncpg``
Skipped automatically if either dependency is missing or Docker is unavailable.
"""

from __future__ import annotations

import asyncio

import pytest

# Skip entire module if testcontainers or asyncpg are not installed
tc = pytest.importorskip(
    "testcontainers.postgres", reason="testcontainers[postgres] not installed"
)
asyncpg = pytest.importorskip("asyncpg", reason="asyncpg not installed")

from testcontainers.postgres import PostgresContainer  # noqa: E402

from core.persistence.pg_key_store import PgKeyStore  # noqa: E402
from core.persistence.pg_decision_store import PgDecisionStore  # noqa: E402


@pytest.fixture(scope="module")
def pg_url():
    """Spin up a real PostgreSQL container and yield the connection URL."""
    try:
        with PostgresContainer("postgres:16-alpine") as pg:
            url = pg.get_connection_url()
            # testcontainers returns psycopg2 URL; convert for asyncpg
            for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
                if url.startswith(prefix):
                    url = "postgresql://" + url[len(prefix) :]
                    break
            yield url
    except Exception as exc:
        pytest.skip(f"Docker not available: {exc}")


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPgKeyStore:
    """Verify PgKeyStore against a real Postgres instance."""

    def test_init_and_tenant_isolation(self, pg_url):
        async def _test():
            import asyncpg as apg

            pool = await apg.create_pool(pg_url)
            try:
                store = PgKeyStore()
                await store.init_db(pool)

                # Create key in tenant_a
                raw, rec = await store.create_key("test-key", tenant_id="tenant_a")
                assert rec.id
                assert rec.status == "active"

                # List keys — only tenant_a sees it
                keys_a = await store.list_keys(tenant_id="tenant_a")
                assert len(keys_a) == 1

                keys_b = await store.list_keys(tenant_id="tenant_b")
                assert len(keys_b) == 0

                # Revoke cross-tenant fails
                revoked = await store.revoke_key(rec.id, tenant_id="tenant_b")
                assert revoked is False

                # Revoke same tenant succeeds
                revoked = await store.revoke_key(rec.id, tenant_id="tenant_a")
                assert revoked is True
            finally:
                await pool.close()

        _run(_test())


class TestPgDecisionStore:
    """Verify PgDecisionStore against a real Postgres instance."""

    def test_claim_and_isolation(self, pg_url):
        async def _test():
            import asyncpg as apg

            pool = await apg.create_pool(pg_url)
            try:
                store = PgDecisionStore()
                await store.init_db(pool)

                # Claim token in tenant_a
                r1 = await store.claim_token(
                    token="tok-1",
                    request_id="r1",
                    policy_version="1.0",
                    manifest_hash="abc",
                    tenant_id="tenant_a",
                )
                assert r1.accepted is True

                # Duplicate in same tenant rejected
                r2 = await store.claim_token(
                    token="tok-1",
                    request_id="r2",
                    policy_version="1.0",
                    manifest_hash="abc",
                    tenant_id="tenant_a",
                )
                assert r2.accepted is False

                # Same token in different tenant is independent
                r3 = await store.claim_token(
                    token="tok-1",
                    request_id="r3",
                    policy_version="1.0",
                    manifest_hash="abc",
                    tenant_id="tenant_b",
                )
                assert r3.accepted is True
            finally:
                await pool.close()

        _run(_test())
