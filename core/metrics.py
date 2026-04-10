"""Aletheia Core — Prometheus metrics.

Exposes operational metrics for monitoring and alerting.
Metrics are served at GET /metrics in OpenMetrics/Prometheus format.
"""

from __future__ import annotations

import time

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

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


def metrics_response() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST
