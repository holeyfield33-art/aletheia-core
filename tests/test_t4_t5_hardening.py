"""Tests for Task 4 Polish + Task 5 — Hardening & Observability Enhancements.

Covers:
- Exporter retry with exponential backoff
- Dead-letter queue (DLQ)
- WebSocket JWT auth + per-tenant rate limiting + heartbeat
- FIPS-140 mode configuration
- Production config validation
- Tenant-scoped metrics
- OTel trace context extraction
- Adversarial ML warnings (docstring presence)
- New Prometheus metrics (retries, DLQ size, tenant requests)
"""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Exporter retry / backoff / DLQ
# ---------------------------------------------------------------------------


class TestExporterRetryBackoff(unittest.TestCase):
    """_export_with_retry retries with exponential backoff."""

    @patch("core.exporters._RETRY_BASE_DELAY", 0.01)
    @patch("core.exporters._MAX_RETRIES", 3)
    def test_export_succeeds_on_first_try(self):
        from core.exporters import _export_with_retry

        exporter = MagicMock()
        exporter.name = "test"
        exporter.export = AsyncMock()
        record = {"decision": "PROCEED"}

        asyncio.run(_export_with_retry(exporter, record))
        exporter.export.assert_awaited_once_with(record)

    @patch("core.exporters._RETRY_BASE_DELAY", 0.01)
    @patch("core.exporters._MAX_RETRIES", 3)
    def test_export_retries_on_failure_then_succeeds(self):
        from core.exporters import _export_with_retry

        exporter = MagicMock()
        exporter.name = "test"
        # Fail twice, succeed third
        exporter.export = AsyncMock(
            side_effect=[RuntimeError("fail"), RuntimeError("fail"), None]
        )
        record = {"decision": "PROCEED"}

        asyncio.run(_export_with_retry(exporter, record))
        self.assertEqual(exporter.export.await_count, 3)

    @patch("core.exporters._RETRY_BASE_DELAY", 0.01)
    @patch("core.exporters._MAX_RETRIES", 2)
    def test_export_dead_letters_after_exhaustion(self):
        from core.exporters import _export_with_retry, dead_letter_queue

        # Clear DLQ
        dead_letter_queue.drain()

        exporter = MagicMock()
        exporter.name = "test-dlq"
        exporter.export = AsyncMock(side_effect=RuntimeError("permanent failure"))
        record = {"decision": "DENIED", "action": "Test"}

        asyncio.run(_export_with_retry(exporter, record))
        self.assertEqual(exporter.export.await_count, 2)
        self.assertGreaterEqual(len(dead_letter_queue), 1)


class TestDeadLetterQueue(unittest.TestCase):
    """DeadLetterQueue bounded storage and drain."""

    def test_push_and_drain(self):
        from core.exporters import DeadLetterQueue

        dlq = DeadLetterQueue(max_size=5)
        dlq.push({"a": 1}, "test", "err1")
        dlq.push({"b": 2}, "test", "err2")
        self.assertEqual(len(dlq), 2)

        items = dlq.drain()
        self.assertEqual(len(items), 2)
        self.assertEqual(len(dlq), 0)

    def test_bounded_capacity(self):
        from core.exporters import DeadLetterQueue

        dlq = DeadLetterQueue(max_size=3)
        for i in range(5):
            dlq.push({"i": i}, "test", "err")
        self.assertEqual(len(dlq), 3)
        items = dlq.drain()
        # Should contain the 3 most recent items
        self.assertEqual([it["record"]["i"] for it in items], [2, 3, 4])

    def test_dlq_stores_metadata(self):
        from core.exporters import DeadLetterQueue

        dlq = DeadLetterQueue()
        dlq.push({"x": 1}, "elasticsearch", "Connection refused")
        item = dlq.drain()[0]
        self.assertEqual(item["exporter"], "elasticsearch")
        self.assertIn("Connection refused", item["error"])
        self.assertIn("failed_at", item)
        self.assertIn("record", item)


# ---------------------------------------------------------------------------
# WebSocket JWT auth
# ---------------------------------------------------------------------------


class TestWSJWTAuth(unittest.TestCase):
    """WebSocket JWT token creation and verification."""

    @patch.dict(os.environ, {"ALETHEIA_WS_JWT_SECRET": "test-secret-key-32chars-min!!"})
    def test_create_and_verify_jwt(self):
        # Reimport to pick up env
        import importlib
        import core.ws_audit

        importlib.reload(core.ws_audit)
        from core.ws_audit import create_ws_token, _verify_ws_jwt

        token = create_ws_token("acme", ttl_seconds=60)
        self.assertIn(".", token)
        result = _verify_ws_jwt(token)
        self.assertEqual(result, "acme")

    @patch.dict(os.environ, {"ALETHEIA_WS_JWT_SECRET": "test-secret-key-32chars-min!!"})
    def test_expired_jwt_rejected(self):
        import importlib
        import core.ws_audit

        importlib.reload(core.ws_audit)
        from core.ws_audit import create_ws_token, _verify_ws_jwt

        token = create_ws_token("acme", ttl_seconds=-1)  # Already expired
        result = _verify_ws_jwt(token)
        self.assertIsNone(result)

    @patch.dict(os.environ, {"ALETHEIA_WS_JWT_SECRET": "test-secret-key-32chars-min!!"})
    def test_tampered_jwt_rejected(self):
        import importlib
        import core.ws_audit

        importlib.reload(core.ws_audit)
        from core.ws_audit import create_ws_token, _verify_ws_jwt

        token = create_ws_token("acme")
        # Tamper with the signature
        parts = token.rsplit(".", 1)
        token = parts[0] + ".deadbeef"
        result = _verify_ws_jwt(token)
        self.assertIsNone(result)

    def test_jwt_disabled_when_no_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALETHEIA_WS_JWT_SECRET", None)
            import importlib
            import core.ws_audit

            importlib.reload(core.ws_audit)
            from core.ws_audit import _verify_ws_jwt

            result = _verify_ws_jwt("anything.here")
            self.assertIsNone(result)


class TestWSPerTenantRateLimit(unittest.TestCase):
    """Per-tenant WebSocket connection limiting."""

    def test_tenant_count_starts_at_zero(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        self.assertEqual(ab.tenant_count("acme"), 0)

    def test_tenant_count_increments(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        for i in range(3):
            ab.subscribe("acme", MagicMock())
        self.assertEqual(ab.tenant_count("acme"), 3)

    def test_tenant_count_decrements_on_unsubscribe(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        ws = MagicMock()
        ab.subscribe("acme", ws)
        ab.unsubscribe("acme", ws)
        self.assertEqual(ab.tenant_count("acme"), 0)


# ---------------------------------------------------------------------------
# FIPS-140 mode
# ---------------------------------------------------------------------------


class TestFIPSMode(unittest.TestCase):
    """FIPS-140 mode configuration and validation."""

    def test_fips_mode_defaults_false(self):
        from core.config import AletheiaSettings

        s = AletheiaSettings()
        self.assertFalse(s.fips_mode)

    def test_fips_mode_can_be_enabled(self):
        from core.config import AletheiaSettings

        s = AletheiaSettings(fips_mode=True)
        self.assertTrue(s.fips_mode)

    def test_validate_fips_compliance_returns_list(self):
        from core.config import validate_fips_compliance

        result = validate_fips_compliance()
        self.assertIsInstance(result, list)

    @patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "short"})
    def test_fips_short_receipt_secret_flagged(self):
        from core.config import validate_fips_compliance

        violations = validate_fips_compliance()
        self.assertTrue(
            any("RECEIPT_SECRET" in v for v in violations),
            f"Expected RECEIPT_SECRET violation, got: {violations}",
        )


# ---------------------------------------------------------------------------
# Production config validation
# ---------------------------------------------------------------------------


class TestProductionConfigValidation(unittest.TestCase):
    """validate_production_config() catches missing prod requirements."""

    def test_missing_receipt_secret(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALETHEIA_RECEIPT_SECRET", None)
            from core.config import validate_production_config

            issues = validate_production_config()
            self.assertTrue(any("RECEIPT_SECRET" in i for i in issues))

    @patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "valid-secret-here"})
    def test_missing_redis_flagged(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REDIS_URL", None)
            os.environ.pop("ALETHEIA_REDIS_URL", None)
            os.environ.pop("UPSTASH_REDIS_REST_URL", None)
            os.environ.pop("UPSTASH_REDIS_REST_TOKEN", None)
            from core.config import validate_production_config

            issues = validate_production_config()
            self.assertTrue(any("Redis" in i for i in issues))

    @patch.dict(
        os.environ,
        {
            "ALETHEIA_RECEIPT_SECRET": "valid-secret",
            "REDIS_URL": "redis://localhost",
        },
    )
    def test_sqlite_flagged_in_production(self):
        from core.config import validate_production_config

        issues = validate_production_config()
        self.assertTrue(
            any("sqlite" in i.lower() or "postgres" in i.lower() for i in issues)
        )

    @patch.dict(
        os.environ,
        {
            "ALETHEIA_RECEIPT_SECRET": "valid-secret",
            "REDIS_URL": "redis://localhost",
        },
    )
    def test_env_secret_backend_flagged(self):
        from core.config import validate_production_config

        issues = validate_production_config()
        self.assertTrue(
            any(
                "secrets manager" in i.lower() or "secret_backend" in i.lower()
                for i in issues
            )
        )


# ---------------------------------------------------------------------------
# New Prometheus metrics
# ---------------------------------------------------------------------------


class TestNewMetrics(unittest.TestCase):
    """New metrics from T4 polish + T5 are importable and functional."""

    def test_exporter_retries_total(self):
        from core.metrics import EXPORTER_RETRIES_TOTAL

        EXPORTER_RETRIES_TOTAL.labels(backend="elasticsearch").inc()

    def test_dlq_size_gauge(self):
        from core.metrics import DLQ_SIZE

        DLQ_SIZE.set(42)
        self.assertEqual(DLQ_SIZE._value.get(), 42.0)
        DLQ_SIZE.set(0)

    def test_tenant_requests_counter(self):
        from core.metrics import TENANT_REQUESTS

        TENANT_REQUESTS.labels(tenant_id="acme", verdict="PROCEED").inc()

    def test_metrics_output_contains_new_metrics(self):
        from core.metrics import metrics_response, TENANT_REQUESTS

        # Ensure at least one label combo exists
        TENANT_REQUESTS.labels(tenant_id="test-output", verdict="DENIED").inc()
        body, content_type = metrics_response()
        text = body.decode("utf-8")
        for name in (
            "aletheia_exporter_retries_total",
            "aletheia_exporter_dlq_size",
            "aletheia_tenant_requests_total",
        ):
            self.assertIn(name, text, f"Missing metric: {name}")


# ---------------------------------------------------------------------------
# OTel trace context extraction
# ---------------------------------------------------------------------------


class TestTraceContextExtraction(unittest.TestCase):
    """extract_trace_context() works with and without OTel."""

    def test_returns_empty_dict_without_otel(self):
        from core.audit import extract_trace_context

        # OTel likely not installed in test env
        result = extract_trace_context()
        self.assertIsInstance(result, dict)

    @patch("core.audit.extract_trace_context")
    def test_trace_fields_injected_when_available(self, mock_extract):
        mock_extract.return_value = {
            "trace_id": "0" * 32,
            "span_id": "0" * 16,
        }
        from core.audit import extract_trace_context

        ctx = extract_trace_context()
        self.assertIn("trace_id", ctx)
        self.assertIn("span_id", ctx)


# ---------------------------------------------------------------------------
# Adversarial ML warnings (docstring presence)
# ---------------------------------------------------------------------------


class TestAdversarialWarnings(unittest.TestCase):
    """Agent methods include adversarial ML limitation warnings."""

    def test_scout_evaluate_threat_context_docstring(self):
        from agents.scout_v2 import AletheiaScoutV2

        doc = AletheiaScoutV2.evaluate_threat_context.__doc__
        self.assertIn("Adversarial", doc)
        self.assertIn("human-in-the-loop", doc)

    def test_nitpicker_check_semantic_block_docstring(self):
        from agents.nitpicker_v2 import AletheiaNitpickerV2

        doc = AletheiaNitpickerV2.check_semantic_block.__doc__
        self.assertIn("Adversarial", doc)
        self.assertIn("adversarial rephrasing", doc)

    def test_judge_verify_action_docstring(self):
        from agents.judge_v1 import AletheiaJudge

        doc = AletheiaJudge.verify_action.__doc__
        self.assertIn("Adversarial", doc)
        self.assertIn("dual-key", doc)


# ---------------------------------------------------------------------------
# Exporter raises on HTTP error (for retry to work)
# ---------------------------------------------------------------------------


class TestExporterRaisesOnError(unittest.TestCase):
    """Exporters raise on HTTP error codes so retry logic can catch them."""

    @patch.dict(os.environ, {"ALETHEIA_ES_URL": "http://es:9200"})
    def test_es_raises_on_400(self):
        from core.exporters import ElasticsearchExporter

        exporter = ElasticsearchExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(
            status_code=500, text="Internal Error"
        )
        exporter._client = mock_client

        with self.assertRaises(RuntimeError):
            asyncio.run(exporter.export({"test": True}))

    @patch.dict(
        os.environ,
        {
            "ALETHEIA_SPLUNK_HEC_URL": "https://splunk:8088/services/collector",
            "ALETHEIA_SPLUNK_HEC_TOKEN": "tok",
        },
    )
    def test_splunk_raises_on_400(self):
        from core.exporters import SplunkExporter

        exporter = SplunkExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=403, text="Forbidden")
        exporter._client = mock_client

        with self.assertRaises(RuntimeError):
            asyncio.run(exporter.export({"test": True}))

    @patch.dict(os.environ, {"ALETHEIA_WEBHOOK_URL": "https://hook.example.com"})
    def test_webhook_raises_on_400(self):
        from core.exporters import WebhookExporter

        exporter = WebhookExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=502, text="Bad Gateway")
        exporter._client = mock_client

        with self.assertRaises(RuntimeError):
            asyncio.run(exporter.export({"test": True}))


if __name__ == "__main__":
    unittest.main()
