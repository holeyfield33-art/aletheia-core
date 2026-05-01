# API Guide

This document summarizes endpoint usage, authentication, and examples.

Detailed endpoint reference is maintained in [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## Authentication

- API key: header `X-API-Key` for `/v1/audit` and `/v1/evaluate`
- Bearer token: `Authorization: Bearer <token>` for RBAC-protected admin endpoints

## Core endpoints

- `POST /v1/audit` - full tri-agent decision with signed receipt
- `POST /v1/evaluate` - lightweight policy decision
- `GET /health` - health probe (returns 503 when dependency checks fail)
- `GET /ready` - readiness probe with manifest and dependency readiness
- `GET /metrics` - Prometheus metrics (when enabled)
- `POST /v1/rotate` - secret rotation (RBAC permission required)

## Example: audit request

```bash
curl -X POST http://localhost:8000/v1/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>" \
  -d '{"payload":"review policy change","origin":"agent-01","action":"Read_Report"}'
```

## Example: evaluate request

```bash
curl -X POST http://localhost:8000/v1/evaluate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api-key>" \
  -d '{"payload":"summarize compliance report","origin":"agent-01","action":"Read_Report"}'
```

## Example: readiness and health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```
