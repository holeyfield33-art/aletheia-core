# API Reference — Aletheia Core v1.9.2

Complete reference for all HTTP endpoints exposed by `bridge/fastapi_wrapper.py`.

Base URL: `http://localhost:8000` (local) or your deployment host.

---

## Authentication

Two authentication mechanisms are supported:

| Header | Used by | Source |
|--------|---------|--------|
| `X-API-Key` | `/v1/audit` | KeyStore (SQLite/Postgres, quota-enforced) |
| `Authorization: Bearer <token>` | All endpoints | OIDC/SAML provider (RBAC permissions) |

API keys are created via `POST /v1/keys` and authenticated exclusively through the KeyStore.
Admin endpoints (`/v1/keys/*`, `/v1/rotate`) require RBAC permissions (e.g. `KEYS_CREATE`, `SECRETS_ROTATE`).
To disable auth in development, set `ALETHEIA_AUTH_DISABLED=true` (blocked in production).

---

## Audit Endpoint

### POST `/v1/audit`

Primary endpoint. Evaluates a payload through the tri-agent pipeline and returns a signed decision.

**Auth:** `X-API-Key` header (required when auth is enabled).

**Request body** (JSON, `Content-Type: application/json`):

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `payload` | string | Yes | max 10,000 chars | The agent action or instruction to evaluate |
| `origin` | string | Yes | max 128 chars | Source identifier (e.g. `trusted_admin`, `agent-01`) |
| `action` | string | Yes | max 128 chars, pattern `^[A-Za-z0-9_\-]+$` | Action identifier (e.g. `Read_Report`, `Transfer_Funds`) |
| `client_ip_claim` | string | No | max 64 chars | Optional client IP for audit logging only — never used for enforcement |

Extra fields are rejected (`extra="forbid"`).

**Response** (200 OK):

```json
{
  "decision": "PROCEED",
  "metadata": {
    "threat_level": "LOW",
    "latency_ms": 14.2,
    "request_id": "a1b2c3d4e5f6g7h8",
    "client_id": "ALETHEIA_ENTERPRISE"
  },
  "receipt": {
    "decision": "PROCEED",
    "policy_hash": "sha256:3d4f...",
    "payload_sha256": "sha256:9a2b...",
    "action": "Read_Report",
    "origin": "trusted_admin",
    "signature": "hmac-sha256:7c1e...",
    "issued_at": "2026-04-10T12:00:00+00:00"
  }
}
```

**Possible `decision` values:**

| Decision | HTTP Status | Meaning |
|----------|-------------|---------|
| `PROCEED` | 200 | Action allowed |
| `DENIED` | 403 | Blocked by Scout threat score, Judge veto, or semantic intent classifier |
| `SANDBOX_BLOCKED` | 403 | Blocked by action sandbox (dangerous pattern detected) |
| `RATE_LIMITED` | 429 | Per-IP rate limit exceeded. `Retry-After: 5` header included. |

**Error responses:**

| Status | Cause |
|--------|-------|
| 401 | Missing or invalid `X-API-Key` |
| 403 | Key revoked or forbidden |
| 422 | Validation error (extra fields, missing fields, pattern mismatch, length exceeded) |
| 429 | Quota exceeded (key store keys). `Retry-After: 86400` header included. |
| 500 | Internal error. No stack trace or internal state is exposed. |
| 503 | Degraded mode — privileged action denied while subsystems are unhealthy |

**Notes:**
- `shadow_verdict` and `redacted_payload` are never returned to clients.
- `reasoning` is never included in PROCEED responses.
- Sandbox match details are never included in SANDBOX_BLOCKED responses.
- Unauthorized tool-invocation attempts (for example `run_in_terminal`, `apply_patch`, `send_to_terminal`, or explicit `tool call` / `function call` control payloads) are blocked with `DENIED` or `SANDBOX_BLOCKED`.
- `threat_level` is discretised: `LOW` (<3.0), `MEDIUM` (3.0–5.99), `HIGH` (6.0–threshold), `CRITICAL` (≥threshold).

---

## Health and Readiness

### GET `/health`

Public health endpoint.

- Without auth: returns minimal status for probes.
- With valid RBAC credentials (admin role): returns extended diagnostics.

**Response (public, 200 OK):**

```json
{
  "status": "ok",
  "service": "aletheia-core"
}
```

**Response (admin diagnostics, 200 OK):**

```json
{
  "status": "ok",
  "service": "aletheia-core",
  "version": "1.9.2",
  "uptime_seconds": 3600.0,
  "timestamp": "2026-04-10T12:00:00+00:00",
  "manifest_signature": "VALID"
}
```

| Field | Values | Meaning |
|-------|--------|---------|
| `status` | `ok`, `degraded` | `degraded` when manifest signature verification fails |
| `manifest_signature` | `VALID`, `INVALID` | Result of Ed25519 signature check (admin diagnostics only) |

### GET `/ready`

Readiness probe. Returns HTTP 200 when all subsystems are healthy, HTTP 503 when degraded.

**Response:**

```json
{
  "ready": true,
  "manifest_signature": "VALID",
  "policy_version": "1.0",
  "receipt_signing_configured": true
}
```

When `ready` is `false` (HTTP 503), privileged actions are denied (fail-closed). Read-only actions continue.

---

## Metrics

### GET `/metrics`

Prometheus/OpenMetrics-format metrics endpoint. No auth required.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `aletheia_requests_total` | Counter | `agent`, `verdict` | Total audit requests processed |
| `aletheia_latency_seconds` | Histogram | — | Request processing latency (buckets: 10ms to 10s) |
| `aletheia_embedding_model_load_seconds` | Gauge | — | Time to load the embedding model at startup |
| `aletheia_keys_total` | Gauge | — | Number of active API keys |
| `aletheia_audit_log_bytes` | Counter | — | Total bytes written to the audit log |

---

## Secret Rotation

### POST `/v1/rotate`

Hot-rotate secrets without restart. Requires RBAC `SECRETS_ROTATE` permission.

**Auth:** `Authorization: Bearer <token>` header with `SECRETS_ROTATE` permission.

**Cooldown:** 10 seconds between rotations. Returns HTTP 429 with `retry_after_seconds` if called within cooldown.

**On rotation, reloads from environment:**
- `ALETHEIA_RECEIPT_SECRET`
- `ALETHEIA_ALIAS_SALT`
- Re-verifies the manifest signature
- Rotates the Judge alias bank

**Success response** (200):

```json
{
  "status": "rotated",
  "receipt_secret_set": true,
  "receipt_secret_length": 64,
  "api_key_count": 2,
  "alias_salt_set": true,
  "admin_key_set": true,
  "api_keys_reloaded": true,
  "judge_reloaded": true,
  "timestamp": 1712750400.0
}
```

**Cooldown response** (429):

```json
{
  "status": "cooldown",
  "retry_after_seconds": 7.3,
  "message": "Rotation too frequent. Wait before retrying."
}
```

**Alternative:** `kill -SIGUSR1 $(pidof python)` performs the same rotation via signal handler.

---

## Key Management

All key management endpoints require RBAC permissions via `Authorization: Bearer <token>` header.

| Endpoint | Required Permission |
|----------|--------------------|
| `POST /v1/keys` | `KEYS_CREATE` |
| `GET /v1/keys` | `KEYS_LIST` |
| `DELETE /v1/keys/{id}` | `KEYS_REVOKE` |
| `GET /v1/keys/{id}/usage` | `KEYS_USAGE` |

### POST `/v1/keys`

Create a new API key.

**Request body:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | Yes | 1–64 chars | Human-readable key name |
| `plan` | string | No | `trial` or `pro` | Plan tier. Default: `trial` |

**Response** (201 Created):

```json
{
  "key": "ak_live_abc123...",
  "id": "k_abc123",
  "name": "my-agent",
  "plan": "trial",
  "monthly_quota": 1000,
  "requests_used": 0,
  "created_at": "2026-04-10T12:00:00+00:00",
  "revoked": false
}
```

The raw `key` value is returned **exactly once** at creation. It is hashed at rest (HMAC-SHA256 with `ALETHEIA_KEY_SALT`, or SHA-256 fallback).

**Default quotas:**
- `trial` (public Free): 1,000 Sovereign Audit Receipts/month
- `pro` (public Scale): 25,000 verified decisions/month
- `max` (public Pro): 100,000 verified decisions/month

Configurable via `ALETHEIA_TRIAL_QUOTA`, `ALETHEIA_PRO_QUOTA`, and `ALETHEIA_MAX_QUOTA` environment variables.

### GET `/v1/keys`

List all API keys (metadata only — no raw keys or hashes).

**Response:**

```json
{
  "keys": [
    {
      "id": "k_abc123",
      "name": "my-agent",
      "plan": "trial",
      "monthly_quota": 1000,
      "requests_used": 42,
      "created_at": "2026-04-10T12:00:00+00:00",
      "revoked": false
    }
  ]
}
```

### DELETE `/v1/keys/{id}`

Revoke an API key by ID.

**Response** (200):

```json
{
  "status": "revoked",
  "id": "k_abc123"
}
```

Returns HTTP 404 if the key does not exist or is already revoked.

### GET `/v1/keys/{id}/usage`

Get usage statistics for a specific key.

**Response** (200):

```json
{
  "id": "k_abc123",
  "name": "my-agent",
  "plan": "trial",
  "monthly_quota": 1000,
  "requests_used": 42,
  "created_at": "2026-04-10T12:00:00+00:00",
  "revoked": false
}
```

Returns HTTP 404 if the key does not exist.

---

## Common Response Headers

All responses include the following security headers:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Cache-Control` | `no-store` |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=(), payment=()` |

Rate-limited responses also include:

| Header | Value |
|--------|-------|
| `X-RateLimit-Remaining` | Remaining requests in the current window |
| `Retry-After` | Seconds until the client can retry |

---

## OpenAPI Schema

FastAPI auto-generates an OpenAPI 3.x schema at runtime:

- **Swagger UI:** `GET /docs`
- **ReDoc:** `GET /redoc`
- **Raw schema:** `GET /openapi.json`

These are available in development. In production, consider disabling them by setting `docs_url=None` and `redoc_url=None` in the FastAPI constructor.

---

## Next.js App Routes

The web dashboard (`app.aletheia-core.com`) exposes the following API routes. All are served by Next.js App Router and are separate from the Python FastAPI backend.

### POST `/api/stripe/checkout`

Creates a Stripe Checkout session for Scale, Pro, or PAYG hosted plans.

**Auth:** NextAuth JWT session (cookie-based). Returns 401 if not authenticated.

**Request:** Optional JSON body or query string selecting the paid tier.

```json
{ "tier": "scale" }
```

Allowed values: `scale`, `pro`, `payg`. If omitted, `scale` is used.

Equivalent query form:

```text
/api/stripe/checkout?tier=payg
```

**Response** (200 OK):

```json
{ "url": "https://checkout.stripe.com/c/pay/cs_..." }
```

The client should redirect the user to the returned URL. On success, the user is redirected to `/dashboard?upgraded=true`. On cancellation, to `/dashboard?upgrade=cancelled`.

**Error responses:**
- `401` — Not authenticated
- `503` — Stripe not configured (missing `STRIPE_SECRET_KEY` or the selected plan price ID)

**Environment variables required:**
- `STRIPE_SECRET_KEY` — Stripe secret key
- `STRIPE_SCALE_PRICE_ID` — Price ID for the Scale subscription
- `STRIPE_PRO_PRICE_ID` — Price ID for the Pro subscription
- `STRIPE_PAYG_METERED_PRICE_ID` — Metered price ID for PAYG

---

### POST `/api/stripe/webhook`

Alias endpoint for Stripe webhook processing (same behavior as `/api/webhooks/stripe`).

---

### POST `/api/webhooks/stripe`

Stripe webhook endpoint for subscription lifecycle events.

**Auth:** Stripe signature verification (`stripe-signature` header, HMAC-SHA256).

**Handled events:**
- `checkout.session.completed` — Upgrades user to the selected paid tier
- `customer.subscription.deleted` — Downgrades user to trial/free tier
- `customer.subscription.updated` — Updates plan based on subscription status

**Environment variables required:**
- `STRIPE_WEBHOOK_SECRET` — Webhook signing secret (`whsec_...`)

---

### PATCH `/api/settings`

Updates the authenticated user's display name.

**Auth:** NextAuth JWT session (cookie-based).

**Request body** (JSON):

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | max 100 chars, trimmed |

**Response** (200 OK):

```json
{ "ok": true }
```

---

### Dashboard Pages

| Path | Description |
|------|-------------|
| `/dashboard` | Overview with stats, onboarding banner (new users), upgrade banner (≥80% quota) |
| `/dashboard/keys` | API key generation, viewing, and revocation |
| `/dashboard/usage` | Per-key request usage and quota monitoring |
| `/dashboard/logs` | Audit decision history with threat analysis |
| `/dashboard/policy` | Security policy configuration viewer |
| `/dashboard/evidence` | Signed audit evidence export (JSONL) |
| `/dashboard/settings` | Account settings: profile, plan/billing, sign out |
