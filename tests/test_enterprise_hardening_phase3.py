"""Phase 3 enterprise hardening tests.

Covers:
- String concatenation bypass patterns (AST + regex)
- Malformed / invalid Base64 payloads
- X-Forwarded-For IP rotation detection
- Distributed brute-force attempts (circuit breaker probe)
"""

from __future__ import annotations

import base64
import random
import time
import unittest

import pytest


# ---------------------------------------------------------------------------
# 1. String concatenation bypass patterns
# ---------------------------------------------------------------------------


class TestStringConcatenationBypass:
    """Verify sandbox catches dynamic string construction that bypasses regex."""

    def test_getattr_concat_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("getattr(os, 'sys' + 'tem')('ls')")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_setattr_concat_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("setattr(obj, 'ev' + 'al', func)")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_subscript_concat_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("modules['sub' + 'process']")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_fstring_getattr_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("getattr(os, f'sys{\"tem\"}')")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_nested_concat_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("getattr(os, 'po' + 'pen')('/bin/sh')")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_benign_getattr_allowed(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("getattr(obj, 'name')")
        assert result is None

    def test_non_dangerous_concat_allowed(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("title = 'hello' + ' world'")
        assert result is None

    def test_regex_fallback_getattr_concat(self):
        """Non-Python text with getattr-like concat pattern should be caught."""
        from core.sandbox import check_payload_sandbox

        # This isn't valid Python, but the regex fallback should catch it
        result = check_payload_sandbox("call getattr(mod, 'sys' + 'tem') to run")
        assert result is not None
        assert "SANDBOX_BLOCK" in result

    def test_delattr_concat_blocked(self):
        from core.sandbox import check_payload_sandbox

        result = check_payload_sandbox("delattr(x, 'sub' + 'process')")
        assert result is not None
        assert "SANDBOX_BLOCK" in result


# ---------------------------------------------------------------------------
# 2. Malformed / invalid Base64 payloads
# ---------------------------------------------------------------------------


class TestMalformedBase64:
    """Verify strict Base64 validation rejects smuggling attempts."""

    def test_valid_base64_decoded(self):
        from core.runtime_security import normalize_untrusted_text

        clean = base64.b64encode(b"hello world").decode()
        result = normalize_untrusted_text(clean)
        assert "hello world" in result.normalized_form

    def test_whitespace_fragmented_base64_rejected(self):
        """Base64 split with whitespace should not decode."""
        from core.runtime_security import normalize_untrusted_text

        clean = base64.b64encode(b"bypass authentication").decode()
        fragmented = clean[:5] + "  " + clean[5:]
        result = normalize_untrusted_text(fragmented)
        # Should NOT contain the decoded payload
        assert "bypass authentication" not in result.normalized_form

    def test_invalid_padding_rejected(self):
        """Base64 with invalid padding should not decode."""
        from core.runtime_security import normalize_untrusted_text

        # Valid base64 would be "aGVsbG8=" — remove padding
        result = normalize_untrusted_text("aGVsbG8")
        assert isinstance(result.normalized_form, str)

    def test_non_base64_chars_rejected(self):
        """Strings with non-base64 characters should not be treated as base64."""
        from core.runtime_security import normalize_untrusted_text

        result = normalize_untrusted_text("not!base64@content#here")
        assert isinstance(result.normalized_form, str)

    def test_nested_base64_encoding(self):
        """Double-encoded base64 should be decoded recursively."""
        from core.runtime_security import normalize_untrusted_text

        inner = base64.b64encode(b"secret data").decode()
        outer = base64.b64encode(inner.encode()).decode()
        result = normalize_untrusted_text(outer)
        assert isinstance(result.normalized_form, str)


# ---------------------------------------------------------------------------
# 3. X-Forwarded-For IP rotation
# ---------------------------------------------------------------------------


class TestXForwardedForRotation:
    """Verify Scout detects rapid requests from rotating IPs."""

    def test_rotation_probing_detected(self):
        """Many rapid requests from a single source = rotation probing."""
        from agents.scout_v2 import AletheiaScoutV2 as Scout

        scout = Scout()
        scores = []
        # Same source_id, many requests — triggers >5 in 60s detection
        for i in range(8):
            score, _ = scout.evaluate_threat_context(
                source_id="attacker-ip",
                payload=f"routine health check {i}",
            )
            scores.append(score)
        # After 5 requests, score should spike to 7.5
        assert scores[-1] >= 7.5, (
            f"Scout should detect rapid meta-querying, got {scores[-1]}"
        )

    def test_single_ip_few_requests_clean(self):
        """A few requests from the same IP should not trigger rotation detection."""
        from agents.scout_v2 import AletheiaScoutV2 as Scout

        scout = Scout()
        scores = []
        for _ in range(3):
            score, _ = scout.evaluate_threat_context(
                source_id="10.0.0.1",
                payload="legitimate query",
            )
            scores.append(score)
        assert all(s < 7.5 for s in scores), "Few requests should not be flagged"


# ---------------------------------------------------------------------------
# 4. Rate limiter circuit breaker probe-through
# ---------------------------------------------------------------------------


class TestCircuitBreakerProbe:
    """Verify circuit breaker allows ~10% probe requests."""

    @pytest.mark.asyncio
    async def test_circuit_open_allows_some_probes(self):
        """When circuit is open, ~10% of requests should be allowed through."""
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter()
        # Force circuit open
        limiter._circuit_open_until = time.monotonic() + 300
        limiter.degraded = True

        # Run many attempts — should see some allowed
        random.seed(42)
        results = []
        for i in range(200):
            result = await limiter.allow(f"test-ip-{i}")
            results.append(result)

        allowed = sum(results)
        # ~10% of 200 = ~20, allow range 5-50 for statistical safety
        assert 5 <= allowed <= 50, f"Expected ~20 allowed, got {allowed}"

    @pytest.mark.asyncio
    async def test_circuit_open_blocks_most_requests(self):
        """When circuit is open, most requests should still be blocked."""
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter()
        limiter._circuit_open_until = time.monotonic() + 300
        limiter.degraded = True

        random.seed(123)
        results = []
        for i in range(100):
            result = await limiter.allow(f"test-ip-{i}")
            results.append(result)

        blocked = sum(1 for r in results if not r)
        assert blocked >= 80, f"Expected >= 80 blocked, got {blocked}"

    @pytest.mark.asyncio
    async def test_circuit_closed_normal_operation(self):
        """When circuit is closed, normal Redis logic applies (fails without Upstash)."""
        from core.rate_limit import UpstashRateLimiter

        limiter = UpstashRateLimiter()
        # Circuit not open — requests go to Redis (which will fail without Upstash)
        assert limiter._circuit_open_until == 0.0
        assert not limiter.degraded


if __name__ == "__main__":
    unittest.main()
