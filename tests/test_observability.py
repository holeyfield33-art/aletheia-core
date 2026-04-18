"""Tests for Task 4 — Centralized Audit Export & Live Observability.

Covers:
- AuditExporter ABC contract
- All four backends (ES, Splunk, Webhook, Syslog) via mocked HTTP
- get_exporters() factory with env-var gating
- enqueue_audit_record() queue semantics
- WebSocket audit broadcast (tenant scoping, PII redaction, auth)
- Expanded Prometheus metrics definitions
- Exporter wiring in log_audit_event()
"""

from __future__ import annotations

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Exporter unit tests
# ---------------------------------------------------------------------------


class TestAuditExporterABC(unittest.TestCase):
    """AuditExporter ABC contract."""

    def test_cannot_instantiate_abc(self):
        from core.exporters import AuditExporter
        with self.assertRaises(TypeError):
            AuditExporter()

    def test_concrete_exporter_requires_name_and_export(self):
        from core.exporters import AuditExporter

        class Bad(AuditExporter):
            pass

        with self.assertRaises(TypeError):
            Bad()


class TestElasticsearchExporter(unittest.TestCase):
    """ElasticsearchExporter posts to ES bulk endpoint."""

    @patch.dict(os.environ, {"ALETHEIA_ES_URL": "http://es:9200"})
    def test_export_calls_httpx_post(self):
        from core.exporters import ElasticsearchExporter

        exporter = ElasticsearchExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=201, text="ok")
        exporter._client = mock_client

        record = {"decision": "PROCEED", "tenant_id": "acme"}
        asyncio.run(exporter.export(record))
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("/_doc", call_args[0][0])

    def test_name_is_elasticsearch(self):
        with patch.dict(os.environ, {"ALETHEIA_ES_URL": "http://es:9200"}):
            from core.exporters import ElasticsearchExporter
            self.assertEqual(ElasticsearchExporter().name, "elasticsearch")


class TestSplunkExporter(unittest.TestCase):
    """SplunkExporter posts to HEC endpoint."""

    @patch.dict(os.environ, {
        "ALETHEIA_SPLUNK_HEC_URL": "https://splunk:8088/services/collector",
        "ALETHEIA_SPLUNK_HEC_TOKEN": "tok",
    })
    def test_export_calls_httpx_post(self):
        from core.exporters import SplunkExporter

        exporter = SplunkExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=200, text="ok")
        exporter._client = mock_client

        record = {"decision": "DENIED", "tenant_id": "beta"}
        asyncio.run(exporter.export(record))
        mock_client.post.assert_called_once()

    def test_name_is_splunk(self):
        with patch.dict(os.environ, {
            "ALETHEIA_SPLUNK_HEC_URL": "https://splunk:8088",
            "ALETHEIA_SPLUNK_HEC_TOKEN": "tok",
        }):
            from core.exporters import SplunkExporter
            self.assertEqual(SplunkExporter().name, "splunk")


class TestWebhookExporter(unittest.TestCase):
    """WebhookExporter posts JSON to an arbitrary URL."""

    @patch.dict(os.environ, {"ALETHEIA_WEBHOOK_URL": "https://hook.example.com/audit"})
    def test_export_calls_httpx_post(self):
        from core.exporters import WebhookExporter

        exporter = WebhookExporter()
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(status_code=200, text="ok")
        exporter._client = mock_client

        record = {"decision": "PROCEED"}
        asyncio.run(exporter.export(record))
        mock_client.post.assert_called_once()

    @patch.dict(os.environ, {
        "ALETHEIA_WEBHOOK_URL": "https://hook.example.com",
        "ALETHEIA_WEBHOOK_SECRET": "s3cret",
    })
    def test_webhook_secret_header(self):
        from core.exporters import WebhookExporter

        exporter = WebhookExporter()
        client = exporter._get_client()
        self.assertEqual(client.headers.get("x-webhook-secret"), "s3cret")

    def test_name_is_webhook(self):
        with patch.dict(os.environ, {"ALETHEIA_WEBHOOK_URL": "https://hook.example.com"}):
            from core.exporters import WebhookExporter
            self.assertEqual(WebhookExporter().name, "webhook")


class TestSyslogExporter(unittest.TestCase):
    """SyslogExporter uses logging.handlers.SysLogHandler."""

    @patch.dict(os.environ, {"ALETHEIA_SYSLOG_HOST": "syslog.local"})
    @patch("logging.handlers.SysLogHandler")
    def test_export_emits_log_record(self, mock_handler_cls):
        from core.exporters import SyslogExporter

        mock_handler = MagicMock()
        mock_handler_cls.return_value = mock_handler

        exporter = SyslogExporter()
        record = {"decision": "DENIED", "action": "Transfer_Funds"}
        asyncio.run(exporter.export(record))
        mock_handler.emit.assert_called_once()

    def test_name_is_syslog(self):
        with patch.dict(os.environ, {"ALETHEIA_SYSLOG_HOST": "syslog.local"}):
            with patch("logging.handlers.SysLogHandler"):
                from core.exporters import SyslogExporter
                self.assertEqual(SyslogExporter().name, "syslog")


class TestGetExporters(unittest.TestCase):
    """get_exporters() returns only backends whose env vars are set."""

    def test_no_env_returns_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove any exporter env vars
            for key in list(os.environ):
                if key.startswith("ALETHEIA_ES_") or key.startswith("ALETHEIA_SPLUNK_") or \
                   key.startswith("ALETHEIA_WEBHOOK_") or key.startswith("ALETHEIA_SYSLOG_"):
                    del os.environ[key]
            from core.exporters import get_exporters
            exporters = get_exporters()
            self.assertEqual(len(exporters), 0)

    @patch.dict(os.environ, {"ALETHEIA_ES_URL": "http://es:9200"})
    def test_only_es_enabled(self):
        from core.exporters import get_exporters
        exporters = get_exporters()
        names = [e.name for e in exporters]
        self.assertIn("elasticsearch", names)

    @patch.dict(os.environ, {"ALETHEIA_WEBHOOK_URL": "https://hook.example.com"})
    def test_only_webhook_enabled(self):
        from core.exporters import get_exporters
        exporters = get_exporters()
        names = [e.name for e in exporters]
        self.assertIn("webhook", names)


class TestEnqueueAuditRecord(unittest.TestCase):
    """enqueue_audit_record() is non-blocking and drops when no exporters."""

    def test_no_crash_when_no_queue(self):
        from core.exporters import enqueue_audit_record
        # Should not raise even if queue is None
        enqueue_audit_record({"decision": "PROCEED"})


# ---------------------------------------------------------------------------
# WebSocket audit broadcast tests
# ---------------------------------------------------------------------------


class TestAuditBroadcast(unittest.TestCase):
    """AuditBroadcast fan-out and tenant scoping."""

    def test_publish_to_matching_tenant(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        mock_ws = MagicMock()
        queue = ab.subscribe("acme", mock_ws)

        ab.publish({"tenant_id": "acme", "decision": "PROCEED"})
        self.assertFalse(queue.empty())
        msg = queue.get_nowait()
        data = json.loads(msg)
        self.assertEqual(data["decision"], "PROCEED")

    def test_publish_does_not_leak_to_other_tenant(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        mock_ws_a = MagicMock()
        mock_ws_b = MagicMock()
        queue_a = ab.subscribe("acme", mock_ws_a)
        queue_b = ab.subscribe("beta", mock_ws_b)

        ab.publish({"tenant_id": "acme", "decision": "PROCEED"})
        self.assertFalse(queue_a.empty())
        self.assertTrue(queue_b.empty())

    def test_admin_sees_all_tenants(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        mock_ws = MagicMock()
        queue = ab.subscribe("__all__", mock_ws)

        ab.publish({"tenant_id": "acme", "decision": "PROCEED"})
        ab.publish({"tenant_id": "beta", "decision": "DENIED"})
        self.assertEqual(queue.qsize(), 2)

    def test_unsubscribe_removes_subscriber(self):
        from core.ws_audit import AuditBroadcast

        ab = AuditBroadcast()
        mock_ws = MagicMock()
        ab.subscribe("acme", mock_ws)
        ab.unsubscribe("acme", mock_ws)
        ab.publish({"tenant_id": "acme", "decision": "PROCEED"})
        # No subscribers = nothing enqueued (no crash)


class TestRedactRecord(unittest.TestCase):
    """WS broadcast must strip sensitive fields and redact PII."""

    def test_strips_payload_fields(self):
        from core.ws_audit import _redact_record

        record = {
            "decision": "PROCEED",
            "payload_sha256": "abc",
            "payload_preview": "some text",
            "payload_length": 42,
            "receipt": {"sig": "x"},
            "action": "Read_Report",
        }
        cleaned = _redact_record(record)
        self.assertNotIn("payload_sha256", cleaned)
        self.assertNotIn("payload_preview", cleaned)
        self.assertNotIn("payload_length", cleaned)
        self.assertNotIn("receipt", cleaned)
        self.assertIn("decision", cleaned)
        self.assertIn("action", cleaned)

    def test_pii_redacted_in_string_fields(self):
        from core.ws_audit import _redact_record

        record = {
            "decision": "DENIED",
            "reason": "User john@evil.com attempted escalation",
        }
        cleaned = _redact_record(record)
        self.assertNotIn("john@evil.com", cleaned.get("reason", ""))
        self.assertIn("[REDACTED:email:", cleaned.get("reason", ""))


class TestWSAuthentication(unittest.TestCase):
    """_authenticate_ws_token must validate tokens properly."""

    def test_admin_key_returns_all(self):
        with patch.dict(os.environ, {"ALETHEIA_ADMIN_KEY": "admin-secret"}):
            from core.ws_audit import _authenticate_ws_token
            result = _authenticate_ws_token("admin-secret")
            self.assertEqual(result, "__all__")

    def test_invalid_token_returns_none(self):
        with patch.dict(os.environ, {"ALETHEIA_ADMIN_KEY": "admin-secret"}):
            from core.ws_audit import _authenticate_ws_token
            result = _authenticate_ws_token("wrong-token")
            self.assertIsNone(result)

    @patch("core.key_store.key_store")
    def test_valid_api_key_returns_tenant(self, mock_ks):
        mock_record = MagicMock()
        mock_record.tenant_id = "acme"
        mock_ks.validate_key.return_value = mock_record

        with patch.dict(os.environ, {"ALETHEIA_ADMIN_KEY": "admin-key"}):
            from core.ws_audit import _authenticate_ws_token
            result = _authenticate_ws_token("user-api-key")
            self.assertEqual(result, "acme")


# ---------------------------------------------------------------------------
# Expanded Prometheus metrics
# ---------------------------------------------------------------------------


class TestExpandedMetrics(unittest.TestCase):
    """New Prometheus metrics are importable and functional."""

    def test_blocked_actions_total(self):
        from core.metrics import BLOCKED_ACTIONS_TOTAL
        BLOCKED_ACTIONS_TOTAL.labels(reason="scout_threat").inc()

    def test_consensus_failures_total(self):
        from core.metrics import CONSENSUS_FAILURES_TOTAL
        CONSENSUS_FAILURES_TOTAL.inc()

    def test_decision_latency(self):
        from core.metrics import DECISION_LATENCY
        DECISION_LATENCY.labels(tenant_id="acme").observe(0.05)

    def test_exporter_errors_total(self):
        from core.metrics import EXPORTER_ERRORS_TOTAL
        EXPORTER_ERRORS_TOTAL.labels(backend="elasticsearch").inc()

    def test_ws_connections_gauge(self):
        from core.metrics import WS_CONNECTIONS
        WS_CONNECTIONS.set(0)
        WS_CONNECTIONS.inc()
        self.assertEqual(WS_CONNECTIONS._value.get(), 1.0)
        WS_CONNECTIONS.dec()
        self.assertEqual(WS_CONNECTIONS._value.get(), 0.0)

    def test_audit_events_exported_counter(self):
        from core.metrics import AUDIT_EVENTS_EXPORTED
        AUDIT_EVENTS_EXPORTED.labels(backend="webhook").inc()

    def test_metrics_output_contains_new_metrics(self):
        from core.metrics import metrics_response
        body, _ = metrics_response()
        text = body.decode("utf-8")
        for name in ("aletheia_blocked_actions_total",
                     "aletheia_exporter_errors_total",
                     "aletheia_ws_audit_connections"):
            self.assertIn(name, text, f"Missing metric: {name}")


# ---------------------------------------------------------------------------
# Integration: exporter dispatch wired into audit pipeline
# ---------------------------------------------------------------------------


class TestExporterWiringInAudit(unittest.TestCase):
    """log_audit_event() dispatches to exporters and WS broadcast."""

    @patch("core.audit._get_audit_logger")
    @patch("core.audit._policy_hash", return_value="abc123")
    @patch("core.audit._policy_version", return_value="1.0")
    @patch("core.exporters.enqueue_audit_record")
    @patch("core.ws_audit.audit_broadcast")
    def test_log_audit_event_calls_enqueue(
        self, mock_broadcast, mock_enqueue, _pv, _ph, mock_logger,
    ):
        mock_logger.return_value.info = lambda x: None
        from core.audit import log_audit_event

        record = log_audit_event(
            decision="PROCEED",
            threat_score=1.0,
            payload="test",
            action="Read_Report",
            source_ip="10.0.0.1",
            origin="trusted_admin",
        )
        mock_enqueue.assert_called_once()
        mock_broadcast.publish.assert_called_once()


# ---------------------------------------------------------------------------
# WebSocket endpoint exists in the FastAPI app
# ---------------------------------------------------------------------------


class TestWSEndpointRegistered(unittest.TestCase):
    """The /ws/audit WebSocket route must be registered on the FastAPI app."""

    def test_ws_audit_route_exists(self):
        from bridge.fastapi_wrapper import app
        ws_routes = [
            r for r in app.routes
            if hasattr(r, "path") and r.path == "/ws/audit"
        ]
        self.assertEqual(len(ws_routes), 1, "/ws/audit route not found")


if __name__ == "__main__":
    unittest.main()
