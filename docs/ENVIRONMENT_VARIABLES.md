# Environment Variables — Aletheia Core v1.7.0

This reference consolidates all environment variables used by the codebase for:
- Local development
- Hosted frontend (Next.js)
- Hosted backend (FastAPI)

Values marked "Hosted" are typically configured in Render/Vercel or your container platform.

---

## 1) Core Backend (FastAPI)

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | Recommended | Yes | Set `production` to enable strict production guards.
| `ACTIVE_MODE` | No | Recommended | Additional production safety confirmation flag.
| `ALETHEIA_MODE` | Recommended | Yes | Runtime mode (`active`, `shadow`, `monitor`).
| `ALETHEIA_API_KEYS` | Optional | Recommended | Comma-separated `X-API-Key` values for `/v1/audit`.
| `ALETHEIA_ADMIN_KEY` | Optional | Yes | Required for admin endpoints and detailed `/health` diagnostics.
| `ALETHEIA_RECEIPT_SECRET` | Recommended | Yes | HMAC key for signed receipts.
| `ALETHEIA_ALIAS_SALT` | Recommended | Recommended | Salt for Judge alias rotation hardening.
| `ALETHEIA_ROTATION_SALT` | Recommended | Recommended | HMAC entropy for Nitpicker mode rotation.
| `ALETHEIA_KEY_SALT` | Recommended | Recommended | Salt for API key hashing.
| `ALETHEIA_MANIFEST_HASH` | Optional | Recommended | Pinned SHA-256 for `manifest/security_policy.json`.
| `ALETHEIA_MANIFEST_KEY_VERSION` | Optional | Optional | Manifest signing key version label (default `v1`).
| `SIGNING_SECRET` | Optional | Yes in strict production mode | Additional production guard (CLI/runtime checks).

---

## 1b) Production Backend & Secrets

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_DATABASE_BACKEND` | Optional | Recommended | `sqlite` (default) or `postgres`. Production validations require `postgres` unless overridden. |
| `DATABASE_URL` | Optional | Yes (if postgres) | PostgreSQL connection string for the audit backend. |
| `ALETHEIA_SECRET_BACKEND` | Optional | Recommended | `env` (default), `vault`, `aws`, `azure`, or `gcp`. |
| `ALETHEIA_ALLOW_ENV_SECRETS` | Optional | Set `true` if using `env` | Acknowledges the risk of using env-var secrets in production. |
| `ALETHEIA_ALLOW_SQLITE_PRODUCTION` | Optional | Set `true` if using `sqlite` | Acknowledges SQLite single-writer limitation for single-worker deploys. |
| `ALETHEIA_FIPS_MODE` | Optional | Optional | Enable FIPS-140 compliance checks at startup. |

---

## 2) Core Runtime Behavior / Policy

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_CONFIG_PATH` | Optional | Optional | Path to YAML config file.
| `ALETHEIA_POLICY_THRESHOLD` | Optional | Optional | Scout block threshold.
| `ALETHEIA_INTENT_THRESHOLD` | Optional | Optional | Judge semantic threshold.
| `ALETHEIA_GREY_ZONE_LOWER` | Optional | Optional | Grey-zone lower bound.
| `ALETHEIA_NITPICKER_SIMILARITY_THRESHOLD` | Optional | Optional | Nitpicker semantic threshold.
| `ALETHEIA_EMBEDDING_MODEL` | Optional | Optional | Embedding model id (`all-MiniLM-L6-v2` default).
| `ALETHEIA_POLYMORPHIC_MODES` | Optional | Optional | Nitpicker mode list override.
| `ALETHEIA_CLIENT_ID` | Optional | Optional | Metadata client ID label.
| `ALETHEIA_LOG_LEVEL` | Optional | Optional | Logging verbosity (`INFO`, `DEBUG`, etc.).
| `ALETHEIA_LOG_PII` | Optional | Optional | `true` disables PII redaction in audit logs.

---

## 3) Storage, Rate Limit, Network

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_AUDIT_LOG_PATH` | Optional | Recommended | Audit log file path.
| `ALETHEIA_KEYSTORE_PATH` | Optional | Recommended | SQLite API key store path.
| `ALETHEIA_DECISION_DB_PATH` | Optional | Recommended | Decision store DB path.
| `UPSTASH_REDIS_REST_URL` | Optional | Recommended (multi-instance) | Redis backend for shared rate limit/replay state.
| `UPSTASH_REDIS_REST_TOKEN` | Optional | Recommended (multi-instance) | Auth token for Upstash Redis.
| `ALETHEIA_RATE_LIMIT_PER_SECOND` | Optional | Optional | Per-IP request limit.
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | Optional | Recommended | Trusted proxy hop count.
| `ALETHEIA_CORS_ORIGINS` | Optional | Recommended | CORS allowlist (comma-separated).
| `ALETHEIA_CORS_ORIGIN` | Optional | Optional | Legacy single-origin CORS setting.
| `ALETHEIA_ALLOWED_BACKEND_HOSTS` | Optional | Recommended | Backend host allowlist for proxy SSRF protection.
| `ALETHEIA_BACKEND_URL` | Optional | Optional | Backend URL used by Next.js API proxy.
| `ALETHEIA_BASE_URL` | Optional | Optional | Canonical base URL for generated links.

---

## 4) Frontend / Auth (Next.js)

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `NODE_ENV` | Auto | Auto | Runtime environment marker.
| `NEXTAUTH_URL` | Yes | Yes | Canonical NextAuth base URL.
| `NEXTAUTH_SECRET` | Yes | Yes | NextAuth signing/encryption secret (32+ chars).
| `DATABASE_URL` | Yes | Yes | Prisma runtime DB connection.
| `DIRECT_URL` | Recommended | Recommended | Prisma direct DB URL for migrations.
| `AUTH_TRUST_HOST` | Optional | Optional | Enables trusted host mode when needed.
| `VERCEL` | Auto | Auto | Set by Vercel runtime.
| `VERCEL_URL` | Auto | Auto | Deployment host set by Vercel.
| `NEXT_PUBLIC_VERCEL_ENV` | Auto | Auto | Vercel environment metadata.
| `NEXT_PUBLIC_VERCEL_URL` | Auto | Auto | Public deployment host.

### Optional OAuth Providers

| Variable | Required | Purpose |
|---|---|---|
| `GITHUB_CLIENT_ID` | Optional | GitHub OAuth login.
| `GITHUB_CLIENT_SECRET` | Optional | GitHub OAuth secret.
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth login.
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth secret.

---

## 5) Billing / Email / Integrations

| Variable | Required Local | Required Hosted | Purpose |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | Optional | Required for billing | Stripe API access for checkout/webhooks.
| `STRIPE_WEBHOOK_SECRET` | Optional | Required for billing | Stripe webhook signature validation.
| `STRIPE_PRO_PRICE_ID` | Optional | Recommended | Stripe Pro plan price id.
| `STRIPE_PRO_PRICE_AMOUNT` | Optional | Optional | Fallback Pro amount if id absent.
| `STRIPE_PRO_CURRENCY` | Optional | Optional | Fallback currency for Pro amount.
| `RESEND_API_KEY` | Optional | Recommended | Transactional email provider key.
| `EMAIL_FROM` | Optional | Recommended | Sender identity for verification emails.
| `HUGGING_FACE_HUB_TOKEN` | Optional | Optional | Auth token for model downloads/rate limits.

---

## 6) Optional Proximity / Advanced Modules

| Variable | Required | Purpose |
|---|---|---|
| `CONSCIOUSNESS_PROXIMITY_ENABLED` | Optional | Enables proximity module.
| `ALETHEIA_ANCHOR_STATE_PATH` | Optional | State path for anchor persistence.
| `MNEME_URL` | Optional | External memory/proximity integration endpoint.
| `MNEME_API_KEY` | Optional | API key for memory/proximity integration.
| `GEOMETRIC_BRAIN_URL` | Optional | Optional advanced relay/scoring integration.
| `ALETHEIA_SMOKE_TIMEOUT` | Optional | Timeout override for smoke script.
| `ALETHEIA_DEMO_ORIGINS` | Optional | Override allowed demo origins.
| `ALETHEIA_DEMO_API_KEY` | Optional | Demo-specific backend API key.
| `ALETHEIA_AUTH_DISABLED` | Optional | Dev bypass for backend auth (never for production).
| `ALETHEIA_API_KEY` | Optional | Single-key compatibility variable in some scripts.

---

## Minimal Working Sets

### Local (dev)

```bash
ENVIRONMENT=development
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<32+ chars>
DATABASE_URL=<postgres connection>
DIRECT_URL=<postgres direct connection>
ALETHEIA_RECEIPT_SECRET=<32+ chars>
```

### Hosted (production baseline)

```bash
ENVIRONMENT=production
ACTIVE_MODE=true
NEXTAUTH_URL=https://app.aletheia-core.com
NEXTAUTH_SECRET=<32+ chars>
DATABASE_URL=<prod connection>
DIRECT_URL=<prod direct connection>
ALETHEIA_MODE=active
ALETHEIA_API_KEYS=<comma-separated>
ALETHEIA_ADMIN_KEY=<strong key>
ALETHEIA_RECEIPT_SECRET=<strong key>
ALETHEIA_ALIAS_SALT=<strong key>
ALETHEIA_ROTATION_SALT=<strong key>
ALETHEIA_KEY_SALT=<strong key>
ALETHEIA_MANIFEST_HASH=<sha256 hex>
```

If horizontally scaled, also set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.
