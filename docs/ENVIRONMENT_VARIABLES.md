# Environment Variables (Code-Verified)

This file is the single source of truth for environment variables used by this repository.

Verification sources:
- Runtime code references: `os.getenv`, `os.environ`, `env_bool`, `process.env`, `import.meta.env`
- Dynamic settings loader in `core/config.py` (`ALETHEIA_<field>` mapping)
- Prisma schema references in `prisma/schema.prisma`

Status meanings:
- Required: startup/functionality fails without it in the stated condition.
- Conditionally required: required only for a mode/feature.
- Optional: default/fallback exists or feature is disabled unless configured.

## Startup Gates (FastAPI)

| Variable | Status | Condition | Why |
| --- | --- | --- | --- |
| ENVIRONMENT | Optional | Always | Enables strict production checks when `production`. |
| ALETHEIA_MODE | Optional | Always | Defaults to `active`; production must run active mode. |
| ALETHEIA_RECEIPT_SECRET | Required | `ALETHEIA_MODE=active` (default) | Startup exits if missing in active mode. |
| ALETHEIA_ALIAS_SALT | Required | `ENVIRONMENT=production` | Startup exits if missing in production. |
| ALETHEIA_KEY_SALT | Required | `ENVIRONMENT=production` | Startup exits if missing in production. |
| REDIS_URL | Conditionally required | `ENVIRONMENT=production` | Required unless Upstash vars are configured. |
| UPSTASH_REDIS_REST_URL | Conditionally required | `ENVIRONMENT=production` | Required with token if `REDIS_URL` is absent. |
| UPSTASH_REDIS_REST_TOKEN | Conditionally required | `ENVIRONMENT=production` | Required with URL if `REDIS_URL` is absent. |
| ALETHEIA_DATABASE_BACKEND | Optional | Always | Default is `sqlite`; `postgres` requires `DATABASE_URL`. |
| ALETHEIA_DATABASE_URL | Optional | Database URL loaded via settings (`ALETHEIA_DATABASE_URL`) as alternative to `DATABASE_URL`. |
| DATABASE_URL | Conditionally required | prod + `ALETHEIA_DATABASE_BACKEND=postgres` | Required and must include `sslmode=require`; for pooled/serverless Postgres add `pgbouncer=true`, otherwise add `statement_cache_size=0` to avoid prepared-statement conflicts. |
| ALETHEIA_ALLOW_SQLITE_PRODUCTION | Conditionally required | prod + sqlite backend | Explicit acknowledgement required for sqlite in prod. |
| ALETHEIA_SECRET_BACKEND | Optional | Always | Default is `env`; can be `vault/aws/azure/gcp`. |
| ALETHEIA_ALLOW_ENV_SECRETS | Conditionally required | prod + `ALETHEIA_SECRET_BACKEND=env` | Explicit acknowledgement required for env-backed secrets in prod. |

## Dynamic Settings Vars (`core/config.py`)

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_EMBEDDING_MODEL | Optional | Embedding model id. |
| ALETHEIA_EMBEDDING_MODEL_REVISION | Optional | Pins embedding model revision/commit for deterministic model loading. |
| ALETHEIA_INTENT_THRESHOLD | Optional | Judge semantic threshold. |
| ALETHEIA_GREY_ZONE_LOWER | Optional | Grey-zone lower bound. |
| ALETHEIA_NITPICKER_SIMILARITY_THRESHOLD | Optional | Nitpicker threshold. |
| ALETHEIA_POLYMORPHIC_MODES | Optional | Override Nitpicker rotation list. |
| ALETHEIA_LOG_LEVEL | Optional | Backend logging level. |
| ALETHEIA_AUDIT_LOG_PATH | Optional | Audit log path in settings model. |
| ALETHEIA_POLICY_THRESHOLD | Optional | Scout deny threshold. |
| ALETHEIA_RATE_LIMIT_PER_SECOND | Optional | Per-IP rate limit. |
| ALETHEIA_CLIENT_ID | Optional | Metadata client id label. |
| ALETHEIA_AUTH_PROVIDER | Optional | Auth provider (`api_key`, `oidc`, `saml`, `multi`). |
| ALETHEIA_OIDC_ISSUER | Optional | OIDC issuer URL. |
| ALETHEIA_OIDC_CLIENT_ID | Optional | OIDC client id. |
| ALETHEIA_OIDC_AUDIENCE | Optional | OIDC JWT audience check. |
| ALETHEIA_OIDC_ROLE_CLAIM | Optional | OIDC role claim key. |
| ALETHEIA_SAML_METADATA_URL | Optional | SAML metadata URL. |
| ALETHEIA_SAML_ENTITY_ID | Optional | SAML SP entity id. |
| ALETHEIA_SAML_ACS_URL | Optional | SAML ACS URL. |
| ALETHEIA_FIPS_MODE | Optional | Enables FIPS compliance checks. |

## Backend Runtime Vars (literal references)

| Variable | Status | Purpose |
| --- | --- | --- |
| ACTIVE_MODE | Optional | CLI/demo launch guard. |
| ALETHEIA_CONFIG_PATH | Optional | YAML config path. |
| ALETHEIA_MANIFEST_HASH | Optional | Manifest hash pinning check. |
| ALETHEIA_MANIFEST_KEY_VERSION | Optional | Manifest key version tag. |
| ALETHEIA_MANIFEST_SIGNATURE_PATH | Optional | Custom manifest signature file path. |
| ALETHEIA_MANIFEST_PUBLIC_KEY_PATH | Optional | Custom manifest public key file path. |
| ALETHEIA_ROTATION_SALT | Optional | HMAC salt used for daily rotation seed fallback logic. |
| ALETHEIA_OPAQUE_DECISIONS | Optional | Hides similarity scores/thresholds in audit responses; defaults ON in production, OFF elsewhere. |
| ALETHEIA_TRUSTED_PROXY_DEPTH | Optional | Trusted reverse-proxy hop depth. |
| ALETHEIA_CORS_ORIGINS | Optional | Backend CORS allowlist. |
| ALETHEIA_CORS_ORIGIN | Optional | Legacy single-origin CORS value (demo route). |
| ALETHEIA_INTERNAL_SECRET | Optional | Internal Vercel->Render trust header secret. |
| ALETHEIA_AUTH_DISABLED | Optional | Dev auth bypass (blocked in production). |
| ALETHEIA_API_KEYS | Legacy/optional | Deprecated env key path; read for warning/block behavior. |
| ALETHEIA_ADMIN_KEY | Legacy/optional | Legacy admin-key compatibility path. |
| ALETHEIA_API_KEY | Optional | Demo proxy fallback API key. |
| ALETHEIA_DEMO_API_KEY | Optional | Preferred demo proxy API key. |
| ALETHEIA_DEMO_ORIGINS | Optional | Demo origins allowlist. |
| ALETHEIA_ALLOWED_BACKEND_HOSTS | Optional | Demo/proxy backend host allowlist. |
| ALETHEIA_BACKEND_URL | Optional | Backend URL for Next.js proxy routes. |
| ALETHEIA_BACKEND_URLS | Optional | Demo backend failover list. |
| ALETHEIA_BASE_URL | Optional | Backend URL fallback for proxies. |
| ALETHEIA_REDIS_URL | Optional | Alternate redis URL checked by production validator. |
| ALETHEIA_KEYSTORE_PATH | Optional | KeyStore sqlite path. |
| ALETHEIA_DECISION_DB_PATH | Optional | Decision-store sqlite path. |
| ALETHEIA_TRIAL_QUOTA | Optional | Trial monthly quota override. |
| ALETHEIA_PRO_QUOTA | Optional | Pro monthly quota override. |
| ALETHEIA_MAX_QUOTA | Optional | Max monthly quota override. |
| DATABASE_LOG_QUERIES | Optional | Slow-query logging toggle. |
| DATABASE_SLOW_QUERY_MS | Optional | Slow-query threshold in ms. |
| EVAL_RATE_LIMIT_PER_MINUTE | Optional | Evaluation limiter per-minute cap. |
| EVAL_RATE_BURST | Optional | Evaluation limiter burst cap. |
| METRICS_ENABLED | Optional | Enables `/metrics`. |
| ALETHEIA_METRICS_TOKEN | Optional | Bearer token required by `/metrics` in production. |
| LOG_FORMAT | Optional | Log output format (`json` or text). |

## TPM / Chain Anchor

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_REQUIRE_TPM | Optional | Hard-fail startup when TPM hardware is unavailable. |
| ALETHEIA_TPM_DEVICE | Optional | TPM device path (default `/dev/tpm0`). |
| ALETHEIA_CHAIN_KEY_PATH | Optional | Software fallback chain key persistence path. |
| ALETHEIA_COUNTER_LOG_PATH | Optional | Counter log path used by TPM sovereignty proof tooling. |

## Receipt Keys / Signing

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_RECEIPT_PRIVATE_KEY | Optional | Inline Ed25519 private key PEM. |
| ALETHEIA_RECEIPT_PRIVATE_KEY_PATH | Optional | File path to Ed25519 private key PEM. |
| ALETHEIA_RECEIPT_PUBLIC_KEY | Optional | Inline Ed25519 public key PEM. |
| ALETHEIA_RECEIPT_PUBLIC_KEY_PATH | Optional | File path to Ed25519 public key PEM. |
| ALETHEIA_RECEIPT_KEY_ID | Optional | Expected 16-char receipt key_id; startup/runtime calls fail if resolved keypair does not match. |
| ALETHEIA_REQUIRE_ED25519_RECEIPTS | Optional (default `true` since v2.0.0) | Enforces Ed25519-only receipt verification path (legacy HMAC receipts rejected). Set to `false` only during HMAC→Ed25519 migration to accept in-flight legacy receipts; plan to remove after the cutover. |
| ALETHEIA_ALLOW_HMAC_RECEIPTS | Optional | Acknowledges the risk of HMAC-only receipts in production when no Ed25519 key is configured; suppresses the corresponding production-config warning. |
| ALETHEIA_MANIFEST_EXPECTED_KEY_ID | Optional | Pins the expected manifest signing public-key fingerprint (sha256); verification rejects an on-disk key that does not match. |
| ALETHEIA_ALLOW_UNPINNED_MANIFEST_KEY | Optional | Acknowledges running without a pinned manifest key fingerprint in production; suppresses the corresponding production-config warning. |
| ALETHEIA_MANIFEST_GRACE_DAYS | Optional | Operator override (>= 0) for the manifest-expiry grace window; production fails closed (0 days) unless set. |
| SIGNING_SECRET | Conditionally required | Required by CLI startup check (`main.py`) in production mode. |

## Semantic / Qdrant

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_SEMANTIC_ENABLED | Optional | Enables Qdrant semantic layer. |
| ALETHEIA_QDRANT_URL | Optional | Qdrant endpoint. |
| ALETHEIA_QDRANT_API_KEY | Optional | Qdrant cloud API key. |
| QDRANT_URL | Optional | Qdrant endpoint used by indexing scripts (for example, scripts/index_qdrant_manifest.py). |
| QDRANT_API_KEY | Optional | Qdrant API key used by indexing scripts (for example, scripts/index_qdrant_manifest.py). |
| ALETHEIA_QDRANT_COLLECTION | Optional | Qdrant collection name. |
| ALETHEIA_QDRANT_TIMEOUT_MS | Optional | Qdrant timeout in ms. |
| ALETHEIA_SEMANTIC_MANIFEST | Optional | Semantic manifest override path. |
| ALETHEIA_DATA_MANIFEST | Optional | Semantic manifest fallback path. |
| HUGGING_FACE_HUB_TOKEN | Optional | Model download auth token. |
| ALETHEIA_MODEL_CACHE_DIR | Optional | Model cache directory override. |

## Exporters / Integrations

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_ES_URL | Optional | Enables Elasticsearch exporter. |
| ALETHEIA_ES_INDEX | Optional | Elasticsearch index name. |
| ALETHEIA_ES_API_KEY | Optional | Elasticsearch API key auth. |
| ALETHEIA_ES_USERNAME | Optional | Elasticsearch basic-auth user. |
| ALETHEIA_ES_PASSWORD | Optional | Elasticsearch basic-auth password. |
| ALETHEIA_SPLUNK_HEC_URL | Optional | Enables Splunk exporter (with token). |
| ALETHEIA_SPLUNK_HEC_TOKEN | Optional | Splunk HEC token. |
| ALETHEIA_SPLUNK_INDEX | Optional | Splunk index. |
| ALETHEIA_SPLUNK_SOURCE | Optional | Splunk source label. |
| ALETHEIA_WEBHOOK_URL | Optional | Enables webhook exporter. |
| ALETHEIA_WEBHOOK_SECRET | Optional | Webhook shared secret header value. |
| ALETHEIA_SYSLOG_HOST | Optional | Enables syslog exporter. |
| ALETHEIA_SYSLOG_PORT | Optional | Syslog port. |
| ALETHEIA_SYSLOG_PROTO | Optional | Syslog protocol (`udp`/`tcp`). |
| ALETHEIA_EXPORTER_MAX_RETRIES | Optional | Export retry count. |
| ALETHEIA_EXPORTER_RETRY_DELAY | Optional | Export retry base delay seconds. |
| ALETHEIA_EXPORTER_DLQ_SIZE | Optional | Dead-letter queue size cap. |

## Secret Backends

| Variable | Status | Purpose |
| --- | --- | --- |
| AWS_REGION | Optional | AWS region for Secrets Manager backend. |
| ALETHEIA_AWS_SECRET_PREFIX | Optional | AWS secret name prefix. |
| AZURE_VAULT_URL | Optional | Azure Key Vault URL. |
| GCP_PROJECT_ID | Optional | GCP project id for Secret Manager. |
| ALETHEIA_GCP_SECRET_PREFIX | Optional | GCP secret prefix. |
| VAULT_ADDR | Optional | Vault server address. |
| VAULT_NAMESPACE | Optional | Vault namespace. |
| VAULT_MOUNT_POINT | Optional | Vault mount point. |
| VAULT_PATH_PREFIX | Optional | Vault path prefix. |
| VAULT_TOKEN | Optional | Vault token auth. |
| VAULT_ROLE_ID | Optional | Vault AppRole role id. |
| VAULT_SECRET_ID | Optional | Vault AppRole secret id. |

## WebSocket Audit

| Variable | Status | Purpose |
| --- | --- | --- |
| ALETHEIA_WS_JWT_SECRET | Optional | JWT secret for websocket token mode. |
| ALETHEIA_WS_MAX_PER_TENANT | Optional | Websocket connection cap per tenant. |
| ALETHEIA_WS_HEARTBEAT_SECONDS | Optional | Websocket heartbeat interval. |

## Frontend (Next.js / Vercel)

| Variable | Status | Purpose |
| --- | --- | --- |
| NODE_ENV | Platform/optional | Node runtime mode checks. |
| NEXTAUTH_SECRET | Conditionally required | Required for NextAuth session/JWT flows. |
| NEXTAUTH_URL | Optional | Canonical auth URL override. |
| VERCEL_URL | Optional | Canonical URL fallback on Vercel. |
| NEXT_PUBLIC_VERCEL_ENV | Optional | UI preview/production hint. |
| NEXT_PUBLIC_VERCEL_URL | Optional | UI deployment host hint. |
| NEXT_PUBLIC_MARKETING_ORIGIN | Optional | Public marketing origin URL. |
| NEXT_PUBLIC_APP_ORIGIN | Optional | Public app origin URL. |
| NEXT_PUBLIC_API_ORIGIN | Optional | Public API origin URL. |
| NEXT_PUBLIC_TRADER_DEMO_VIDEO_URL | Optional | Public homepage demo video URL. |
| NEXT_PUBLIC_TRADER_DEMO_POSTER_URL | Optional | Public poster/thumbnail URL for direct video playback. |
| AUTH_CLAIM_REFRESH_MS | Optional | Frontend auth claim refresh interval. |
| CSP_EXTRA_CONNECT_SRC | Optional | Extra CSP connect-src values. |
| TRUST_CF_HEADERS | Optional | Use Cloudflare headers for client IP extraction. |
| GITHUB_CLIENT_ID | Optional | GitHub OAuth provider client id. |
| GITHUB_CLIENT_SECRET | Optional | GitHub OAuth provider client secret. |
| GOOGLE_CLIENT_ID | Optional | Google OAuth provider client id. |
| GOOGLE_CLIENT_SECRET | Optional | Google OAuth provider client secret. |

## Billing / Email / Cron

| Variable | Status | Purpose |
| --- | --- | --- |
| STRIPE_SECRET_KEY | Conditionally required | Stripe checkout and usage-report routes. |
| STRIPE_WEBHOOK_SECRET | Conditionally required | Stripe webhook verification (required in production path). |
| STRIPE_SCALE_PRICE_ID | Optional | Hosted scale plan price id. |
| STRIPE_PRO_PRICE_ID | Optional | Hosted pro plan price id. |
| STRIPE_PAYG_METERED_PRICE_ID | Optional | PAYG metered price id. |
| STRIPE_SCALE_PRICE_AMOUNT | Optional | Scale plan amount fallback. |
| STRIPE_PRO_PRICE_AMOUNT | Optional | Pro plan amount fallback. |
| STRIPE_SCALE_CURRENCY | Optional | Scale currency fallback. |
| STRIPE_PRO_CURRENCY | Optional | Pro currency fallback. |
| STRIPE_PAYG_METERED_CURRENCY | Optional | PAYG metered currency fallback. |
| STRIPE_PAYG_CURRENCY | Optional | PAYG currency fallback. |
| CRON_SECRET | Conditionally required | Auth secret for usage cron route. |
| SLACK_WEBHOOK_URL | Optional | Usage report destination. |
| RESEND_API_KEY | Optional | Transactional email provider key. |
| EMAIL_FROM | Optional | Email sender override. |

## Demo Proxy Runtime Tuning

| Variable | Status | Purpose |
| --- | --- | --- |
| DEMO_UPSTREAM_TIMEOUT_MS | Optional | Demo upstream timeout. |
| DEMO_UPSTREAM_ATTEMPTS_PER_BACKEND | Optional | Attempts per backend target. |
| DEMO_UPSTREAM_RETRY_BACKOFF_MS | Optional | Retry backoff delay. |
| DEMO_RATE_LIMIT | Optional | Demo per-IP rate limit. |
| DEMO_RATE_WINDOW_MS | Optional | Demo rate-limit window. |
| DEMO_NONCE_SECRET | Optional | HMAC secret for demo nonce/receipt guard fallback. |

## Proximity Module

| Variable | Status | Purpose |
| --- | --- | --- |
| CONSCIOUSNESS_PROXIMITY_ENABLED | Optional | Enables optional proximity subsystem. |
| MNEME_URL | Optional | Mneme endpoint URL. |
| MNEME_API_KEY | Optional | Mneme API key. |
| GEOMETRIC_BRAIN_URL | Optional | Geometric brain endpoint URL. |
| SPECTRAL_POLL_INTERVAL | Optional | Spectral poll interval seconds. |
| SPECTRAL_DEGRADATION_THRESHOLD | Optional | Spectral degradation threshold. |
| SPECTRAL_DEGRADATION_CONSECUTIVE | Optional | Consecutive degradation threshold count. |
| ALETHEIA_ANCHOR_STATE_PATH | Optional | Anchor state persistence path. |

## Prisma Tooling

`prisma/schema.prisma` references:

| Variable | Status | Purpose |
| --- | --- | --- |
| DATABASE_URL | Required for Prisma commands | Prisma datasource URL. |
| DIRECT_URL | Optional | Prisma direct URL for migrations/introspection. |

## Non-runtime (test/CI/script-only) variables in repo

These are present outside runtime app code (tests/workflows/scripts):

- ALETHEIA_ANOTHER_SECRET
- ALETHEIA_API_URL
- ALETHEIA_AUTH_HEADER
- ALETHEIA_DISABLE_TEST_STUBS
- PYTEST_CURRENT_TEST
- ALETHEIA_TRIFECTA_URL
- ALETHEIA_SMOKE_TIMEOUT
- ALETHEIA_TEST_SECRET
- ALETHEIA_TRIFECTA_URL
- ALETHEIA_WARMUP_URL
- ALETHEIA_WARMUP_TIMEOUT_SECONDS
- ALETHEIA_WARMUP_DELAY_SECONDS
