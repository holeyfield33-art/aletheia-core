# Aletheia Core Helm Chart

Production-grade Kubernetes deployment for Aletheia Core.

## Quick Start

```bash
# Dev mode (SQLite, in-memory rate limiting)
helm install aletheia charts/aletheia-core \
  --set config.mode=shadow \
  --set secrets.receiptSecret=$(openssl rand -hex 32)

# Production (Postgres + Redis)
helm install aletheia charts/aletheia-core \
  --values charts/aletheia-core/values-production.yaml \
  --set secrets.receiptSecret=$RECEIPT_SECRET \
  --set secrets.apiKeys=$API_KEYS \
  --set secrets.keySalt=$KEY_SALT \
  --set secrets.aliasSalt=$ALIAS_SALT
```

## Security Features

- Non-root container (UID 65534)
- Read-only root filesystem
- All capabilities dropped
- Seccomp profile: RuntimeDefault
- Network policies restricting ingress/egress
- Pod disruption budget for HA
- Secrets managed via Kubernetes Secret or ExternalSecrets Operator

## Configuration

See [values.yaml](values.yaml) for all available options.

## Observability

### Prometheus

A `ServiceMonitor` is included (disabled by default). Enable it for Prometheus Operator:

```yaml
serviceMonitor:
  enabled: true
  interval: 30s
  path: /metrics
```

Metrics are served at the `/metrics` endpoint (see main README for the full metrics table).

### Audit Exporters

Configure external audit export backends via `config.*` in `values.yaml`:

```yaml
config:
  esUrl: "https://es.internal:9200"
  splunkHecUrl: "https://splunk:8088/services/collector"
  webhookUrl: "https://siem.corp/aletheia"
  syslogHost: "syslog.internal"
```

All exporters are non-blocking. Failures are logged but never block the audit pipeline.

### WebSocket Audit Stream

`/ws/audit?token=<api_key>` provides a live, tenant-scoped, PII-redacted event stream.
Admin keys see events from all tenants.
