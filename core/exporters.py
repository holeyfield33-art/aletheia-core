"""Aletheia Core — Pluggable audit export framework.

Provides AuditExporter ABC and four concrete backends:
  - ElasticsearchExporter  (bulk index via httpx)
  - SplunkExporter         (HEC via httpx)
  - WebhookExporter        (generic HTTP POST)
  - SyslogExporter         (RFC 5424 via Python logging.handlers)

Exporters are configured via environment variables and instantiated
by ``get_exporters()``, which returns all enabled backends.

All export is **fire-and-forget async** — failures are retried with
exponential backoff and dead-lettered after max attempts.
A persistent ``asyncio.Queue`` feeds a background drain task started
by ``start_export_workers()``.
"""

from __future__ import annotations

import abc
import asyncio
import json
import logging
import os
import time
from collections import deque
from typing import Any

_logger = logging.getLogger("aletheia.exporters")

# Retry configuration
_MAX_RETRIES: int = int(os.getenv("ALETHEIA_EXPORTER_MAX_RETRIES", "3"))
_RETRY_BASE_DELAY: float = float(os.getenv("ALETHEIA_EXPORTER_RETRY_DELAY", "1.0"))
_DLQ_MAX_SIZE: int = int(os.getenv("ALETHEIA_EXPORTER_DLQ_SIZE", "1000"))

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AuditExporter(abc.ABC):
    """Interface for pluggable audit export backends."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""

    @abc.abstractmethod
    async def export(self, record: dict[str, Any]) -> None:
        """Send a single audit record to the backend.

        Raise on failure — the drain loop handles retry/backoff.
        """

    async def close(self) -> None:
        """Release resources (called at shutdown)."""


# ---------------------------------------------------------------------------
# Dead-letter queue
# ---------------------------------------------------------------------------


class DeadLetterQueue:
    """Bounded in-memory dead-letter queue for failed export records."""

    def __init__(self, max_size: int = _DLQ_MAX_SIZE) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=max_size)

    def push(self, record: dict[str, Any], exporter_name: str, error: str) -> None:
        self._items.append(
            {
                "record": record,
                "exporter": exporter_name,
                "error": str(error)[:500],
                "failed_at": time.time(),
            }
        )

    def drain(self) -> list[dict[str, Any]]:
        """Return and clear all items."""
        items = list(self._items)
        self._items.clear()
        return items

    def __len__(self) -> int:
        return len(self._items)


dead_letter_queue = DeadLetterQueue()


# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------


class ElasticsearchExporter(AuditExporter):
    """Export audit records to Elasticsearch / OpenSearch.

    Env vars:
        ALETHEIA_ES_URL          — Base URL (required)
        ALETHEIA_ES_INDEX        — Index name (default: aletheia-audit)
        ALETHEIA_ES_API_KEY      — API key (optional, for Elastic Cloud)
        ALETHEIA_ES_USERNAME     — Basic auth user (optional)
        ALETHEIA_ES_PASSWORD     — Basic auth password (optional)
    """

    def __init__(self) -> None:
        self._url = os.getenv("ALETHEIA_ES_URL", "").rstrip("/")
        self._index = os.getenv("ALETHEIA_ES_INDEX", "aletheia-audit")
        self._api_key = os.getenv("ALETHEIA_ES_API_KEY", "")
        self._username = os.getenv("ALETHEIA_ES_USERNAME", "")
        self._password = os.getenv("ALETHEIA_ES_PASSWORD", "")
        self._client = None

    @property
    def name(self) -> str:
        return "elasticsearch"

    def _get_client(self) -> Any:
        if self._client is None:
            import httpx

            headers = {"Content-Type": "application/json"}
            auth = None
            if self._api_key:
                headers["Authorization"] = f"ApiKey {self._api_key}"
            elif self._username:
                auth = (self._username, self._password)
            self._client = httpx.AsyncClient(
                base_url=self._url,
                headers=headers,
                auth=auth,
                timeout=10.0,
            )
        return self._client

    async def export(self, record: dict[str, Any]) -> None:
        client = self._get_client()
        resp = await client.post(
            f"/{self._index}/_doc",
            content=json.dumps(record, default=str),
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"ES {resp.status_code}: {resp.text[:200]}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Splunk HEC
# ---------------------------------------------------------------------------


class SplunkExporter(AuditExporter):
    """Export audit records to Splunk via HTTP Event Collector (HEC).

    Env vars:
        ALETHEIA_SPLUNK_HEC_URL    — HEC endpoint (required)
        ALETHEIA_SPLUNK_HEC_TOKEN  — HEC token (required)
        ALETHEIA_SPLUNK_INDEX      — Target index (optional)
        ALETHEIA_SPLUNK_SOURCE     — Source label (default: aletheia-core)
    """

    def __init__(self) -> None:
        self._url = os.getenv("ALETHEIA_SPLUNK_HEC_URL", "").rstrip("/")
        self._token = os.getenv("ALETHEIA_SPLUNK_HEC_TOKEN", "")
        self._index = os.getenv("ALETHEIA_SPLUNK_INDEX", "")
        self._source = os.getenv("ALETHEIA_SPLUNK_SOURCE", "aletheia-core")
        self._client = None

    @property
    def name(self) -> str:
        return "splunk"

    def _get_client(self) -> Any:
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Splunk {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        return self._client

    async def export(self, record: dict[str, Any]) -> None:
        client = self._get_client()
        event = {
            "event": record,
            "source": self._source,
            "sourcetype": "_json",
        }
        if self._index:
            event["index"] = self._index
        resp = await client.post(self._url, content=json.dumps(event, default=str))
        if resp.status_code >= 400:
            raise RuntimeError(f"Splunk HEC {resp.status_code}: {resp.text[:200]}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Generic HTTP Webhook
# ---------------------------------------------------------------------------


class WebhookExporter(AuditExporter):
    """POST audit records to an arbitrary HTTP endpoint.

    Env vars:
        ALETHEIA_WEBHOOK_URL     — Target URL (required)
        ALETHEIA_WEBHOOK_SECRET  — Shared secret (sent as X-Webhook-Secret header)
    """

    def __init__(self) -> None:
        self._url = os.getenv("ALETHEIA_WEBHOOK_URL", "")
        self._secret = os.getenv("ALETHEIA_WEBHOOK_SECRET", "")
        self._client = None

    @property
    def name(self) -> str:
        return "webhook"

    def _get_client(self) -> Any:
        if self._client is None:
            import httpx

            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._secret:
                headers["X-Webhook-Secret"] = self._secret
            self._client = httpx.AsyncClient(headers=headers, timeout=10.0)
        return self._client

    async def export(self, record: dict[str, Any]) -> None:
        client = self._get_client()
        resp = await client.post(self._url, content=json.dumps(record, default=str))
        if resp.status_code >= 400:
            raise RuntimeError(f"Webhook {resp.status_code}: {resp.text[:200]}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Syslog (RFC 5424)
# ---------------------------------------------------------------------------


class SyslogExporter(AuditExporter):
    """Export audit records via syslog (UDP or TCP).

    Env vars:
        ALETHEIA_SYSLOG_HOST     — Syslog server host (default: localhost)
        ALETHEIA_SYSLOG_PORT     — Port (default: 514)
        ALETHEIA_SYSLOG_PROTO    — "udp" or "tcp" (default: udp)
    """

    def __init__(self) -> None:
        import logging.handlers

        host = os.getenv("ALETHEIA_SYSLOG_HOST", "localhost")
        port = int(os.getenv("ALETHEIA_SYSLOG_PORT", "514"))
        proto = os.getenv("ALETHEIA_SYSLOG_PROTO", "udp").lower()
        socktype = None
        if proto == "tcp":
            import socket

            socktype = socket.SOCK_STREAM
        self._handler = logging.handlers.SysLogHandler(
            address=(host, port),
            socktype=socktype,
        )
        self._handler.setFormatter(logging.Formatter("aletheia-core: %(message)s"))

    @property
    def name(self) -> str:
        return "syslog"

    async def export(self, record: dict[str, Any]) -> None:
        msg = json.dumps(record, default=str)
        log_record = logging.LogRecord(
            name="aletheia.audit",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        self._handler.emit(log_record)

    async def close(self) -> None:
        self._handler.close()


# ---------------------------------------------------------------------------
# Factory + background drain with retry/backoff
# ---------------------------------------------------------------------------

_export_queue: asyncio.Queue[dict[str, Any]] | None = None
_drain_task: asyncio.Task | None = None
_exporters: list[AuditExporter] = []


def get_exporters() -> list[AuditExporter]:
    """Instantiate all enabled exporters based on environment variables."""
    exporters: list[AuditExporter] = []
    if os.getenv("ALETHEIA_ES_URL"):
        exporters.append(ElasticsearchExporter())
        _logger.info("Audit exporter enabled: elasticsearch")
    if os.getenv("ALETHEIA_SPLUNK_HEC_URL") and os.getenv("ALETHEIA_SPLUNK_HEC_TOKEN"):
        exporters.append(SplunkExporter())
        _logger.info("Audit exporter enabled: splunk")
    if os.getenv("ALETHEIA_WEBHOOK_URL"):
        exporters.append(WebhookExporter())
        _logger.info("Audit exporter enabled: webhook")
    if os.getenv("ALETHEIA_SYSLOG_HOST"):
        exporters.append(SyslogExporter())
        _logger.info("Audit exporter enabled: syslog")
    return exporters


async def _export_with_retry(
    exporter: AuditExporter,
    record: dict[str, Any],
) -> None:
    """Attempt export with exponential backoff; dead-letter on exhaustion."""
    from core.metrics import (
        EXPORTER_ERRORS_TOTAL,
        AUDIT_EVENTS_EXPORTED,
        EXPORTER_RETRIES_TOTAL,
        DLQ_SIZE,
    )

    for attempt in range(_MAX_RETRIES):
        try:
            await exporter.export(record)
            AUDIT_EVENTS_EXPORTED.labels(backend=exporter.name).inc()
            return
        except Exception as exc:
            EXPORTER_ERRORS_TOTAL.labels(backend=exporter.name).inc()
            if attempt < _MAX_RETRIES - 1:
                EXPORTER_RETRIES_TOTAL.labels(backend=exporter.name).inc()
                delay = _RETRY_BASE_DELAY * (2**attempt)
                _logger.warning(
                    "Exporter %s attempt %d/%d failed: %s — retrying in %.1fs",
                    exporter.name,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                _logger.error(
                    "Exporter %s exhausted %d retries — dead-lettering record",
                    exporter.name,
                    _MAX_RETRIES,
                )
                dead_letter_queue.push(record, exporter.name, str(exc))
                DLQ_SIZE.set(len(dead_letter_queue))


async def _drain_loop(
    queue: asyncio.Queue[dict[str, Any]],
    exporters: list[AuditExporter],
) -> None:
    """Background task: pull records from the queue and fan-out to all exporters."""
    while True:
        record = await queue.get()
        for exporter in exporters:
            await _export_with_retry(exporter, record)
        queue.task_done()


def start_export_workers() -> asyncio.Queue[dict[str, Any]] | None:
    """Initialise exporters and start the background drain task.

    Returns the queue to publish records to, or None if no exporters are enabled.
    """
    global _export_queue, _drain_task, _exporters
    _exporters = get_exporters()
    if not _exporters:
        _logger.info("No audit exporters configured — external export disabled")
        return None
    _export_queue = asyncio.Queue(maxsize=10_000)
    _drain_task = asyncio.create_task(_drain_loop(_export_queue, _exporters))
    _logger.info("Audit export workers started (%d exporters)", len(_exporters))
    return _export_queue


async def stop_export_workers() -> None:
    """Flush queue and close all exporters (call during shutdown)."""
    global _drain_task, _export_queue
    if _drain_task is not None:
        _drain_task.cancel()
        try:
            await _drain_task
        except asyncio.CancelledError:
            pass
        _drain_task = None
    for exporter in _exporters:
        try:
            await exporter.close()
        except Exception as exc:
            _logger.warning("Exporter %s close error: %s", exporter.name, exc)
    _export_queue = None


def enqueue_audit_record(record: dict[str, Any]) -> None:
    """Non-blocking enqueue of an audit record for external export.

    Silently drops records if the queue is full or no exporters are configured.
    """
    if _export_queue is None:
        return
    try:
        _export_queue.put_nowait(record)
    except asyncio.QueueFull:
        _logger.warning("Audit export queue full — dropping record")
