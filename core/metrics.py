"""Aletheia Core — Prometheus metrics.

Exposes operational metrics for monitoring and alerting.
Metrics are served at GET /metrics in OpenMetrics/Prometheus format.
"""

from __future__ import annotations


from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

REQUEST_COUNTER = Counter(
    "aletheia_requests_total",
    "Total audit requests processed",
    ["agent", "verdict"],
)

LATENCY_HISTOGRAM = Histogram(
    "aletheia_latency_seconds",
    "Request processing latency",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

EMBEDDING_LOAD_SECONDS = Gauge(
    "aletheia_embedding_model_load_seconds",
    "Time taken to load the embedding model at startup",
)

ACTIVE_KEYS = Gauge(
    "aletheia_keys_total",
    "Number of active API keys",
)

AUDIT_LOG_BYTES = Counter(
    "aletheia_audit_log_bytes",
    "Total bytes written to the audit log",
)

# --- Task 4: Observability expansion ---

BLOCKED_ACTIONS_TOTAL = Counter(
    "aletheia_blocked_actions_total",
    "Total actions blocked by the pipeline",
    ["reason"],
)

CONSENSUS_FAILURES_TOTAL = Counter(
    "aletheia_consensus_failures_total",
    "Consensus / TMR receipt failures",
)

DECISION_LATENCY = Histogram(
    "aletheia_decision_latency_seconds",
    "Per-tenant decision latency",
    ["tenant_id"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

EXPORTER_ERRORS_TOTAL = Counter(
    "aletheia_exporter_errors_total",
    "Audit export backend failures",
    ["backend"],
)

WS_CONNECTIONS = Gauge(
    "aletheia_ws_audit_connections",
    "Active WebSocket audit stream connections",
)

AUDIT_EVENTS_EXPORTED = Counter(
    "aletheia_audit_events_exported_total",
    "Audit events dispatched to external exporters",
    ["backend"],
)

EXPORTER_RETRIES_TOTAL = Counter(
    "aletheia_exporter_retries_total",
    "Total retry attempts for audit export backends",
    ["backend"],
)

DLQ_SIZE = Gauge(
    "aletheia_exporter_dlq_size",
    "Number of records in the dead-letter queue",
)

TENANT_REQUESTS = Counter(
    "aletheia_tenant_requests_total",
    "Total audit requests per tenant",
    ["tenant_id", "verdict"],
)


AUDIT_DECISIONS_TOTAL = Counter(
    "aletheia_audit_decisions_total",
    "Total audit decisions by outcome",
    ["decision"],
)

AUDIT_EVALUATION_DURATION_SECONDS = Histogram(
    "aletheia_audit_evaluation_duration_seconds",
    "Full decision processing time for /v1/audit",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def metrics_response() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST
