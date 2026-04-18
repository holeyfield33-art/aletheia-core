"""Tests for the persistence abstraction layer (core/persistence/).

Covers:
  - tenant_scope() validation and default fallback
  - redis_tenant_key() formatting with tenant isolation
  - Invalid tenant_id rejection (empty, traversal, injection)
"""

from __future__ import annotations

import pytest

from core.persistence import DEFAULT_TENANT, tenant_scope, redis_tenant_key


class TestTenantScope:
    """Hard tenant isolation: tenant_scope() must ALWAYS return a valid ID."""

    def test_none_returns_default(self):
        assert tenant_scope(None) == DEFAULT_TENANT

    def test_valid_tenant(self):
        assert tenant_scope("acme") == "acme"

    def test_strips_whitespace(self):
        assert tenant_scope("  acme  ") == "acme"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            tenant_scope("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            tenant_scope("   ")

    def test_path_traversal_rejected(self):
        for bad in ("../escape", "a/b", "a\\b", "a\x00b", "id;DROP", "test..prod"):
            with pytest.raises(ValueError, match="Illegal characters"):
                tenant_scope(bad)

    def test_default_constant(self):
        assert DEFAULT_TENANT == "default"


class TestRedisTenantKey:
    """Every Redis key must be namespaced by tenant."""

    def test_basic_format(self):
        assert redis_tenant_key("acme", "rl", "10.0.0.1") == "tenant:acme:rl:10.0.0.1"

    def test_none_tenant_uses_default(self):
        assert redis_tenant_key(None, "decision", "tok123") == "tenant:default:decision:tok123"

    def test_different_tenants_different_keys(self):
        k1 = redis_tenant_key("tenant_a", "rl", "ip1")
        k2 = redis_tenant_key("tenant_b", "rl", "ip1")
        assert k1 != k2

    def test_invalid_tenant_rejects(self):
        with pytest.raises(ValueError):
            redis_tenant_key("../bad", "rl", "ip")
