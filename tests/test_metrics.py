"""Tests for Prometheus metrics endpoint and instrumentation."""
from __future__ import annotations

import unittest


class TestMetricsModule(unittest.TestCase):
    """Test core/metrics.py metric definitions."""

    def test_metrics_response_returns_bytes(self):
        from core.metrics import metrics_response
        body, content_type = metrics_response()
        self.assertIsInstance(body, bytes)
        self.assertIn("text/", content_type)

    def test_request_counter_increments(self):
        from core.metrics import REQUEST_COUNTER
        before = REQUEST_COUNTER.labels(agent="test", verdict="PROCEED")._value.get()
        REQUEST_COUNTER.labels(agent="test", verdict="PROCEED").inc()
        after = REQUEST_COUNTER.labels(agent="test", verdict="PROCEED")._value.get()
        self.assertEqual(after, before + 1)

    def test_latency_histogram_observe(self):
        from core.metrics import LATENCY_HISTOGRAM
        # Should not raise
        LATENCY_HISTOGRAM.observe(0.05)

    def test_metrics_output_contains_aletheia_prefix(self):
        from core.metrics import metrics_response
        body, _ = metrics_response()
        text = body.decode("utf-8")
        self.assertIn("aletheia_requests_total", text)
        self.assertIn("aletheia_latency_seconds", text)


if __name__ == "__main__":
    unittest.main()
