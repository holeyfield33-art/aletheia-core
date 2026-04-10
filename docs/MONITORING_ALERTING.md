# Monitoring & Alerting Guide — Aletheia Core v1.6.2

Prometheus metrics, recommended alert rules, and operational health checks.

---

## Exported Metrics

Aletheia Core exports Prometheus metrics at `GET /metrics`.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `aletheia_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests handled |
| `aletheia_latency_seconds` | Histogram | `endpoint` | Request latency distribution |
| `aletheia_embedding_model_load_seconds` | Gauge | — | Time (seconds) to load the sentence-transformers embedding model |
| `aletheia_keys_total` | Gauge | — | Current number of registered API keys |
| `aletheia_audit_log_bytes` | Gauge | — | Current size of the audit log file in bytes |

---

## Prometheus Scrape Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: aletheia
    scrape_interval: 15s
    metrics_path: /metrics
    static_configs:
      - targets: ["aletheia-core:8080"]
```

---

## Recommended Alert Rules

### Request Rate Anomalies

```yaml
groups:
  - name: aletheia-alerts
    rules:
      # No requests in 5 minutes — possible outage
      - alert: AletheiaNoRequests
        expr: rate(aletheia_requests_total[5m]) == 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Aletheia Core has received no requests for 5 minutes"
          runbook: "Check /health and /ready endpoints"

      # Error rate > 5% over 5 minutes
      - alert: AletheiaHighErrorRate
        expr: |
          sum(rate(aletheia_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(aletheia_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Aletheia Core error rate exceeds 5%"
          runbook: "Check application logs for ManifestTamperedError or dependency failures"
```

### Latency

```yaml
      # p99 latency > 2 seconds
      - alert: AletheiaHighLatency
        expr: |
          histogram_quantile(0.99, rate(aletheia_latency_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Aletheia Core p99 latency exceeds 2 seconds"
          runbook: "Check embedding model load time and Redis connectivity"
```

### Embedding Model

```yaml
      # Model took > 30 seconds to load (cold start)
      - alert: AletheiaSlowModelLoad
        expr: aletheia_embedding_model_load_seconds > 30
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Embedding model load took {{ $value }}s"
          runbook: "Consider pre-warming or caching the model"
```

### Audit Log Size

```yaml
      # Audit log > 100 MB
      - alert: AletheiaAuditLogLarge
        expr: aletheia_audit_log_bytes > 100 * 1024 * 1024
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Audit log size is {{ $value | humanize1024 }}B"
          runbook: "Rotate logs using logrotate (see deploy/logrotate.conf)"
```

### API Key Count

```yaml
      # No API keys registered
      - alert: AletheiaNoApiKeys
        expr: aletheia_keys_total == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Aletheia Core has no registered API keys"
          runbook: "Register keys via POST /v1/keys"
```

---

## Health Check Endpoints

### GET /health

Returns `200 OK` with `{"status": "ok"}` if the process is running.
Use for liveness probes (Kubernetes `livenessProbe`, Render health checks).

```yaml
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 15
```

### GET /ready

Returns `200 OK` with readiness details:

```json
{
  "ready": true,
  "manifest_ok": true,
  "embedding_model_loaded": true,
  "policy_version": "2026.03.07",
  "manifest_hash": "a1b2c3..."
}
```

If any component is not ready, returns `503 Service Unavailable`.
Use for readiness probes — do not route traffic until `/ready` returns 200.

```yaml
# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 10
```

---

## Grafana Dashboard Suggestions

### Request Overview Panel

```
rate(aletheia_requests_total[5m])
```
Split by `status` label to distinguish 2xx, 4xx, 5xx.

### Latency Heatmap

```
aletheia_latency_seconds_bucket
```
Use the Grafana histogram panel type.

### Audit Decision Ratio

```
sum(rate(aletheia_requests_total{endpoint="/v1/audit", status="200"}[5m]))
```
Overlay with denied responses (status 403) for decision trend analysis.

### Key Store Gauge

```
aletheia_keys_total
```
Single-stat panel showing current active key count.

---

## Operational Alerts (Non-Prometheus)

These checks should be scripted or managed through your deployment platform:

| Check | Method | Frequency | Action on Failure |
|-------|--------|-----------|-------------------|
| Health | `curl /health` | 30s | Restart container |
| Readiness | `curl /ready` | 60s | Hold traffic, investigate |
| Manifest expiry | Parse `expires_at` from `/ready` | Daily | Re-sign manifest (see `docs/KEY_ROTATION.md`) |
| SQLite backup | `scripts/backup_sqlite.sh` | Daily | Alert ops team |
| Log rotation | `logrotate deploy/logrotate.conf` | Daily | Check `aletheia_audit_log_bytes` metric |
| Certificate expiry | Check TLS cert | Weekly | Renew before expiry |

---

## Log-Based Monitoring

Key log patterns to watch for:

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `ManifestTamperedError` | CRITICAL | Ed25519 signature verification failed |
| `manifest expired` | WARNING | Manifest past `expires_at` (7-day grace) |
| `drift detected` | ERROR | Workers have mismatched policy versions |
| `rate limit exceeded` | INFO | Client hit rate limiter |
| `rotation completed` | INFO | Secret rotation triggered successfully |
| `ALETHEIA_ALIAS_SALT not set` | WARNING | Alias rotation is predictable |
| `config ownership` | ERROR | Config file has unsafe permissions |
