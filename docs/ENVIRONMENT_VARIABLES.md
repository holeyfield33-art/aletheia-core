# Environment Variables

<!-- markdownlint-disable MD013 -->

Aletheia Core v1.9.2 environment reference.

- **Local**: development defaults
- **Hosted**: Render / Vercel / container platform

---

## 1) Core Backend (FastAPI)

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | Recommended | Yes | Set `production` for strict guards. |
| `ACTIVE_MODE` | No | Recommended | Production safety confirmation. |
| `ALETHEIA_MODE` | Recommended | Yes | `active`, `shadow`, `monitor`. |
| ~~`ALETHEIA_API_KEYS`~~ | — | **Removed** | Removed in v1.9.0. Use KeyStore (`POST /v1/keys`). |
| ~~`ALETHEIA_ADMIN_KEY`~~ | — | **Removed** | Removed in v1.9.0. Use RBAC permissions. |
| `ALETHEIA_RECEIPT_SECRET` | Recommended | Yes | HMAC key for signed receipts. |
| `ALETHEIA_ALIAS_SALT` | Recommended | Recommended | Judge alias rotation salt. |
| `ALETHEIA_ROTATION_SALT` | Recommended | Recommended | Nitpicker mode rotation HMAC. |
| `ALETHEIA_KEY_SALT` | Recommended | Recommended | Salt for API key hashing. |
| `ALETHEIA_MANIFEST_HASH` | Optional | Recommended | Pinned SHA-256 of manifest. |
| `ALETHEIA_MANIFEST_KEY_VERSION` | Optional | Optional | Key version (default `v1`). |
| `SIGNING_SECRET` | Optional | Yes (strict) | Production guard (CLI/runtime). |

---

## 1b) Production Backend & Secrets

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_DATABASE_BACKEND` | Optional | Recommended | `sqlite` or `postgres`. |
| `DATABASE_URL` | Optional | Yes (postgres) | Postgres connection string. |
| `ALETHEIA_SECRET_BACKEND` | Optional | Recommended | `env`/`vault`/`aws`/`azure`/`gcp`. |
| `ALETHEIA_ALLOW_ENV_SECRETS` | Optional | If using `env` | Opt-in for env secrets in prod. |
| ~~`ALETHEIA_ALLOW_SQLITE_PRODUCTION`~~ | — | **Removed** | Removed in v1.9.0. Production requires Upstash Redis. |
| `ALETHEIA_FIPS_MODE` | Optional | Optional | FIPS-140 compliance checks. |

---

## 2) Core Runtime / Policy

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_CONFIG_PATH` | Optional | Optional | YAML config file path. |
| `ALETHEIA_POLICY_THRESHOLD` | Optional | Optional | Scout block threshold. |
| `ALETHEIA_INTENT_THRESHOLD` | Optional | Optional | Judge semantic threshold. |
| `ALETHEIA_GREY_ZONE_LOWER` | Optional | Optional | Grey-zone lower bound. |
| `ALETHEIA_NITPICKER_SIMILARITY_THRESHOLD` | Optional | Optional | Nitpicker threshold. |
| `ALETHEIA_EMBEDDING_MODEL` | Optional | Optional | Default `sentence-transformers/all-MiniLM-L6-v2`. |
| `ALETHEIA_MODEL_CACHE_DIR` | Optional | Optional | Override local model cache root (default `~/.cache/aletheia/models`). |
| `ALETHEIA_POLYMORPHIC_MODES` | Optional | Optional | Nitpicker mode list override. |
| `ALETHEIA_CLIENT_ID` | Optional | Optional | Metadata client ID label. |
| `ALETHEIA_LOG_LEVEL` | Optional | Optional | `INFO`, `DEBUG`, etc. |
| ~~`ALETHEIA_LOG_PII`~~ | — | **Removed** | Removed in v1.9.0. PII is always redacted. |

---

## 3) Storage, Rate Limit, Network

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `ALETHEIA_AUDIT_LOG_PATH` | Optional | Recommended | Audit log file path. |
| `ALETHEIA_KEYSTORE_PATH` | Optional | Recommended | SQLite API key store path. |
| `ALETHEIA_DECISION_DB_PATH` | Optional | Recommended | Decision store DB path. |
| `UPSTASH_REDIS_REST_URL` | Optional | **Yes** | Redis for rate limit/replay/decision store. Required in production. |
| `UPSTASH_REDIS_REST_TOKEN` | Optional | **Yes** | Upstash Redis auth token. Required in production. |
| `ALETHEIA_RATE_LIMIT_PER_SECOND` | Optional | Optional | Per-IP request limit. |
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | Optional | Recommended | Trusted proxy hop count. |
| `ALETHEIA_CORS_ORIGINS` | Optional | Recommended | CORS allowlist (comma-sep). |
| `ALETHEIA_CORS_ORIGIN` | Optional | Optional | Legacy single-origin CORS. |
| `ALETHEIA_ALLOWED_BACKEND_HOSTS` | Optional | Recommended | SSRF backend allowlist. |
| `ALETHEIA_BACKEND_URL` | Optional | Optional | Next.js API proxy URL. |
| `ALETHEIA_BASE_URL` | Optional | Optional | Canonical base URL for links. |

---

## 4) Frontend / Auth (Next.js)

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `NODE_ENV` | Auto | Auto | Runtime environment marker. |
| `NEXTAUTH_URL` | Yes | Yes | NextAuth canonical base URL. |
| `NEXTAUTH_SECRET` | Yes | Yes | Signing secret (32+ chars). |
| `DATABASE_URL` | Yes | Yes | Prisma runtime DB connection. |
| `DIRECT_URL` | Recommended | Recommended | Prisma direct URL for migrations. |
| `AUTH_TRUST_HOST` | Optional | Optional | Trusted host mode. |
| `VERCEL` | Auto | Auto | Set by Vercel runtime. |
| `VERCEL_URL` | Auto | Auto | Deployment host from Vercel. |
| `NEXT_PUBLIC_VERCEL_ENV` | Auto | Auto | Vercel environment metadata. |
| `NEXT_PUBLIC_VERCEL_URL` | Auto | Auto | Public deployment host. |

### Optional OAuth Providers

| Variable | Required | Purpose |
|---|---|---|
| `GITHUB_CLIENT_ID` | Optional | GitHub OAuth login. |
| `GITHUB_CLIENT_SECRET` | Optional | GitHub OAuth secret. |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth login. |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth secret. |

---

## 5) Billing / Email / Integrations

| Variable | Local | Hosted | Purpose |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | Optional | For billing | Stripe API key. |
| `STRIPE_WEBHOOK_SECRET` | Optional | For billing | Stripe webhook signature. |
| `STRIPE_SCALE_PRICE_ID` | Optional | Recommended | Scale plan price id. |
| `STRIPE_SCALE_PRICE_AMOUNT` | Optional | Optional | Fallback Scale amount. |
| `STRIPE_SCALE_CURRENCY` | Optional | Optional | Fallback Scale currency. |
| `STRIPE_PRO_PRICE_ID` | Optional | Recommended | Pro plan price id. |
| `STRIPE_PRO_PRICE_AMOUNT` | Optional | Optional | Fallback Pro amount. |
| `STRIPE_PRO_CURRENCY` | Optional | Optional | Fallback currency. |
| `STRIPE_PAYG_METERED_PRICE_ID` | Optional | Recommended | PAYG metered price id. |
| `STRIPE_PAYG_METERED_CURRENCY` | Optional | Optional | PAYG currency. |
| `CRON_SECRET` | Optional | Recommended | Bearer secret for usage-report cron endpoint auth. |
| `RESEND_API_KEY` | Optional | Recommended | Transactional email key. |
| `EMAIL_FROM` | Optional | Recommended | Sender identity. |
| `HUGGING_FACE_HUB_TOKEN` | Optional | Optional | Model download auth token. |

---

## 6) Optional Proximity / Advanced

| Variable | Required | Purpose |
|---|---|---|
| `CONSCIOUSNESS_PROXIMITY_ENABLED` | Optional | Enable proximity module. |
| `ALETHEIA_ANCHOR_STATE_PATH` | Optional | Anchor persistence path. |
| `MNEME_URL` | Optional | Memory/proximity endpoint. |
| `MNEME_API_KEY` | Optional | Memory/proximity API key. |
| `GEOMETRIC_BRAIN_URL` | Optional | Advanced relay/scoring. |
| `ALETHEIA_SMOKE_TIMEOUT` | Optional | Smoke script timeout override. |
| `ALETHEIA_DEMO_ORIGINS` | Optional | Allowed demo origins. |
| `ALETHEIA_DEMO_API_KEY` | Optional | Vercel `/api/demo` server-side key sent as `X-API-Key` to backend. |
| `ALETHEIA_AUTH_DISABLED` | Optional | Dev auth bypass (never prod). |
| `ALETHEIA_API_KEY` | Optional | Fallback for `/api/demo` when `ALETHEIA_DEMO_API_KEY` is unset. |

<!-- markdownlint-enable MD013 -->

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
ALETHEIA_RECEIPT_SECRET=<strong key>
ALETHEIA_ALIAS_SALT=<strong key>
ALETHEIA_ROTATION_SALT=<strong key>
ALETHEIA_KEY_SALT=<strong key>
ALETHEIA_MANIFEST_HASH=<sha256 hex>
UPSTASH_REDIS_REST_URL=<upstash url>
UPSTASH_REDIS_REST_TOKEN=<upstash token>
```

API keys are created via `POST /v1/keys` (KeyStore). Admin endpoints
use RBAC permissions (OIDC/SAML bearer tokens). Upstash Redis is
required for production deployments (rate limiting, replay defense,
decision store).

### Demo Proxy Env (Vercel + Render)

- Set on Vercel:
	- `ALETHEIA_BACKEND_URL=https://aletheia-core.onrender.com`
	- `ALETHEIA_ALLOWED_BACKEND_HOSTS=aletheia-core.onrender.com,app.aletheia-core.com,aletheia-core.com`
	- `ALETHEIA_DEMO_API_KEY=<key-from-POST-/v1/keys>` (or `ALETHEIA_API_KEY` as fallback)
- On Render: also set `ALETHEIA_DEMO_API_KEY` to the **same value** if your KeyStore
  uses the default SQLite backend on an ephemeral filesystem (e.g. Render free tier).
  The backend's lifespan hook will idempotently re-import the key on every restart.
  Skip this only if `ALETHEIA_DATABASE_BACKEND=postgres` with a durable `DATABASE_URL`.
- For long-lived deploys, prefer Postgres: set `ALETHEIA_DATABASE_BACKEND=postgres` and
  `DATABASE_URL`, then provision the demo key once via `POST /v1/keys`.

See `docs/LAUNCH_GUIDE.md` → "Hosted demo key persistence" for the full runbook.
