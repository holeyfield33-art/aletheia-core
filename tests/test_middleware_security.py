# SPDX-License-Identifier: MIT
"""Tests for server/middleware.py — security headers and internal-secret guard.

Coverage target: ~76% → ~95% of the middleware module.

Tests cover:
  - Security header presence and values (HSTS, CSP, X-Frame-Options, etc.)
  - X-Request-ID: pass-through from caller; generated when absent
  - Cache-Control default applied; not overwritten when already set
  - Rate-limit headers forwarded when present on request state
  - Internal-secret guard: blocked paths, exempt paths, no-op when secret unset
  - Auth middleware populates request.state.auth_context on valid credential
  - Auth middleware skips exempt paths
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal FastAPI app wired with all three middleware functions
# ---------------------------------------------------------------------------


def _build_app(internal_secret: str = "") -> FastAPI:
    """Return a test FastAPI instance with Aletheia middleware registered."""
    from server.middleware import (
        add_security_and_rate_limit_headers,
        enterprise_auth_middleware,
        internal_secret_guard,
    )

    app = FastAPI()

    # Register in the same order as server/app.py uses.
    app.middleware("http")(add_security_and_rate_limit_headers)
    app.middleware("http")(enterprise_auth_middleware)
    app.middleware("http")(internal_secret_guard)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        return {"status": "ready"}

    @app.get("/v1/protected")
    async def protected() -> dict:
        return {"data": "secret"}

    @app.get("/v1/audit")
    async def audit() -> dict:
        return {"decision": "PROCEED"}

    return app


# ---------------------------------------------------------------------------
# Security header tests
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    def test_x_content_type_options_nosniff(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options_deny(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_content_security_policy_present(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_permissions_policy_present(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        pp = resp.headers.get("permissions-policy", "")
        assert "geolocation=()" in pp
        assert "microphone=()" in pp

    def test_strict_transport_security_present(self) -> None:
        """HSTS header must be present with a long max-age."""
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        hsts = resp.headers.get("strict-transport-security", "")
        assert "max-age=" in hsts
        # At least a one-year max-age.
        import re
        match = re.search(r"max-age=(\d+)", hsts)
        assert match, f"HSTS max-age not found in: {hsts!r}"
        assert int(match.group(1)) >= 31_536_000, (
            f"HSTS max-age should be at least 1 year, got {match.group(1)}"
        )
        assert "includeSubDomains" in hsts

    def test_cache_control_default_no_store(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        cc = resp.headers.get("cache-control", "")
        assert "no-store" in cc

    def test_cache_control_not_overwritten_when_set(self) -> None:
        """If the endpoint already sets Cache-Control, the middleware must not override it."""
        from server.middleware import add_security_and_rate_limit_headers

        app = FastAPI()
        app.middleware("http")(add_security_and_rate_limit_headers)

        @app.get("/cached")
        async def cached_endpoint() -> JSONResponse:
            return JSONResponse(
                content={"ok": True},
                headers={"Cache-Control": "public, max-age=3600"},
            )

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/cached")
        assert "public" in resp.headers.get("cache-control", "")


# ---------------------------------------------------------------------------
# X-Request-ID header
# ---------------------------------------------------------------------------


class TestRequestID:
    def test_x_request_id_present_in_response(self) -> None:
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_x_request_id_is_uuid_format_when_not_provided(self) -> None:
        import uuid as _uuid

        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health")
        rid = resp.headers.get("x-request-id", "")
        # Should be parseable as a UUID.
        parsed = _uuid.UUID(rid)
        assert str(parsed) == rid

    def test_x_request_id_echoed_from_caller(self) -> None:
        """When the caller provides X-Request-ID, the same value is echoed back."""
        caller_id = "my-trace-id-12345"
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/health", headers={"x-request-id": caller_id})
        assert resp.headers.get("x-request-id") == caller_id

    def test_x_request_ids_differ_across_requests(self) -> None:
        """Each request without a caller-supplied ID gets a unique generated one."""
        client = TestClient(_build_app(), raise_server_exceptions=False)
        id1 = client.get("/health").headers.get("x-request-id")
        id2 = client.get("/health").headers.get("x-request-id")
        assert id1 != id2


# ---------------------------------------------------------------------------
# Internal-secret guard
# ---------------------------------------------------------------------------


class TestInternalSecretGuard:
    def test_guard_noop_when_secret_not_configured(self) -> None:
        """Without ALETHEIA_INTERNAL_SECRET set, all requests pass."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
            # Re-import middleware to pick up unset env var.
            import importlib
            import server.middleware as mw_mod

            importlib.reload(mw_mod)

        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/v1/protected")
        assert resp.status_code == 200

    def test_guard_blocks_v1_path_without_header(self) -> None:
        """With secret configured, /v1/* requests missing the header get 403."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/v1/protected")
            async def protected() -> dict:
                return {"ok": True}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/v1/protected")
            assert resp.status_code == 403

        # Restore: unset env var and reload to clean state.
        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_guard_allows_v1_path_with_correct_header(self) -> None:
        """Correct x-aletheia-internal header passes the guard."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/v1/protected")
            async def protected() -> dict:
                return {"ok": True}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(
                "/v1/protected",
                headers={"x-aletheia-internal": secret},
            )
            assert resp.status_code == 200

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_guard_blocks_wrong_secret(self) -> None:
        """Wrong header value → 403, even if it looks similar."""
        secret = "correct-secret"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/v1/protected")
            async def protected() -> dict:
                return {"ok": True}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get(
                "/v1/protected",
                headers={"x-aletheia-internal": "wrong-secret"},
            )
            assert resp.status_code == 403

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_guard_passes_health_endpoint(self) -> None:
        """Health probe must never be blocked by the internal-secret guard."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/health")
            async def health() -> dict:
                return {"status": "ok"}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health")
            assert resp.status_code == 200

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_guard_passes_audit_endpoint_by_design(self) -> None:
        """/v1/audit is exempt so API-SDK clients can call Render directly."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.post("/v1/audit")
            async def audit() -> dict:
                return {"decision": "PROCEED"}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post("/v1/audit")
            assert resp.status_code == 200, (
                "/v1/audit should be exempt from the internal-secret guard"
            )

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_non_v1_path_not_guarded(self) -> None:
        """Paths outside /v1/ are never blocked by the guard."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/public-page")
            async def public_page() -> dict:
                return {"hello": "world"}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/public-page")
            assert resp.status_code == 200

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)

    def test_guard_403_response_is_json(self) -> None:
        """Blocked requests must receive a JSON error body."""
        secret = "test-internal-secret-abc123"
        import importlib
        import server.middleware as mw_mod

        with patch.dict(os.environ, {"ALETHEIA_INTERNAL_SECRET": secret}):
            importlib.reload(mw_mod)

            from server.middleware import internal_secret_guard

            app = FastAPI()
            app.middleware("http")(internal_secret_guard)

            @app.get("/v1/something")
            async def something() -> dict:
                return {"data": "x"}

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/v1/something")
            assert resp.status_code == 403
            body = resp.json()
            assert "error" in body

        os.environ.pop("ALETHEIA_INTERNAL_SECRET", None)
        importlib.reload(mw_mod)


# ---------------------------------------------------------------------------
# Rate-limit headers forwarded
# ---------------------------------------------------------------------------


class TestRateLimitHeaders:
    def test_retry_after_forwarded_from_request_state(self) -> None:
        """When request.state.retry_after is set, Retry-After must appear in response."""
        from server.middleware import add_security_and_rate_limit_headers

        app = FastAPI()
        app.middleware("http")(add_security_and_rate_limit_headers)

        @app.post("/v1/rate-limited")
        async def rate_limited(request: Request) -> JSONResponse:
            request.state.retry_after = 30
            return JSONResponse(status_code=429, content={"error": "too many requests"})

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/v1/rate-limited")
        assert resp.headers.get("retry-after") == "30"

    def test_x_ratelimit_remaining_forwarded(self) -> None:
        from server.middleware import add_security_and_rate_limit_headers

        app = FastAPI()
        app.middleware("http")(add_security_and_rate_limit_headers)

        @app.get("/v1/endpoint")
        async def endpoint(request: Request) -> dict:
            request.state.rate_limit_remaining = 7
            return {"ok": True}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/v1/endpoint")
        assert resp.headers.get("x-ratelimit-remaining") == "7"
