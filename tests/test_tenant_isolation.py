"""Hard tenant isolation tests — proves no cross-tenant leakage.

These tests create data in tenant_A and verify tenant_B cannot see, list,
revoke, or otherwise access it.  This is the CRITICAL guarantee for
multi-tenancy safety.
"""

from __future__ import annotations


import pytest

from core.key_store import KeyStore
from core.audit import log_audit_event


@pytest.fixture()
def isolated_key_store(tmp_path):
    """Provide a fresh KeyStore with an isolated temp DB."""
    db = str(tmp_path / "keys.db")
    return KeyStore(db_path=db)


class TestKeyStoreTenantIsolation:
    """Prove that keys created in one tenant are invisible to another."""

    def test_create_in_A_invisible_to_B(self, isolated_key_store):
        ks = isolated_key_store
        raw, rec = ks.create_key("k1", tenant_id="tenant_a")

        # Visible in tenant_a
        assert ks.get_by_id(rec.id, tenant_id="tenant_a") is not None
        assert ks.lookup_by_hash(raw, tenant_id="tenant_a") is not None

        # Invisible in tenant_b
        assert ks.get_by_id(rec.id, tenant_id="tenant_b") is None
        assert ks.lookup_by_hash(raw, tenant_id="tenant_b") is None

    def test_list_keys_scoped_by_tenant(self, isolated_key_store):
        ks = isolated_key_store
        ks.create_key("k_a1", tenant_id="tenant_a")
        ks.create_key("k_a2", tenant_id="tenant_a")
        ks.create_key("k_b1", tenant_id="tenant_b")

        assert len(ks.list_keys(tenant_id="tenant_a")) == 2
        assert len(ks.list_keys(tenant_id="tenant_b")) == 1
        # Default tenant sees nothing
        assert len(ks.list_keys(tenant_id="default")) == 0

    def test_revoke_cross_tenant_fails(self, isolated_key_store):
        ks = isolated_key_store
        _, rec = ks.create_key("k1", tenant_id="tenant_a")

        # tenant_b cannot revoke tenant_a's key
        assert ks.revoke_key(rec.id, tenant_id="tenant_b") is False

        # Key still active in tenant_a
        fetched = ks.get_by_id(rec.id, tenant_id="tenant_a")
        assert fetched is not None
        assert fetched.status == "active"

    def test_check_and_increment_cross_tenant(self, isolated_key_store):
        ks = isolated_key_store
        raw, rec = ks.create_key("k1", tenant_id="tenant_a")

        # Works in tenant_a
        result = ks.check_and_increment(raw, tenant_id="tenant_a")
        assert result.allowed is True

        # Fails in tenant_b (key not found → not allowed)
        result_b = ks.check_and_increment(raw, tenant_id="tenant_b")
        assert result_b.allowed is False

    def test_none_tenant_defaults_to_default(self, isolated_key_store):
        ks = isolated_key_store
        _, rec = ks.create_key("k1", tenant_id=None)

        # Visible under "default"
        assert ks.get_by_id(rec.id, tenant_id="default") is not None
        assert ks.get_by_id(rec.id, tenant_id=None) is not None

        # Not visible under other tenants
        assert ks.get_by_id(rec.id, tenant_id="other") is None


class TestAuditTenantFields:
    """Verify audit records carry tenant_id, user_id, auth_method."""

    def test_audit_record_contains_tenant_fields(self):
        rec = log_audit_event(
            decision="PROCEED",
            threat_score=0.1,
            payload="test",
            action="ping",
            source_ip="127.0.0.1",
            origin="test",
            tenant_id="acme",
            user_id="u-123",
            auth_method="oidc",
        )
        assert rec["tenant_id"] == "acme"
        assert rec["user_id"] == "u-123"
        assert rec["auth_method"] == "oidc"

    def test_audit_default_tenant(self):
        rec = log_audit_event(
            decision="DENIED",
            threat_score=9.0,
            payload="evil",
            action="nuke",
            source_ip="10.0.0.1",
            origin="test",
        )
        assert rec["tenant_id"] == "default"
        assert rec["user_id"] == ""
        assert rec["auth_method"] == ""
