# Operations Runbook — Aletheia Core v1.9.2

This document covers day-to-day operations, environment setup, and troubleshooting
for a production Aletheia Core deployment.

Canonical env matrix: `docs/ENVIRONMENT_VARIABLES.md`

---

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALETHEIA_MODE` | Yes | `active` (production) / `shadow` (dev, log-only) / `monitor` |
| `ALETHEIA_RECEIPT_SECRET` | Yes (active) | HMAC signing secret for audit receipts. Min 32 chars. Generate: `openssl rand -hex 32` |
| `UPSTASH_REDIS_REST_URL` | Yes (production) | Upstash Redis URL for rate limiting, replay defense, and decision store |
| `UPSTASH_REDIS_REST_TOKEN` | Yes (production) | Upstash Redis auth token |
| `ALETHEIA_ALIAS_SALT` | Recommended | Salt for daily alias rotation. Generate: `openssl rand -hex 32` |
| `ALETHEIA_KEY_SALT` | Recommended | HMAC salt for key store hashing. Falls back to plain SHA-256 if unset |
| `ALETHEIA_ANCHOR_STATE_PATH` | Optional | Path for proximity module identity anchor state persistence (requires `CONSCIOUSNESS_PROXIMITY_ENABLED=true`) |
| `ALETHEIA_LOG_LEVEL` | Optional | `INFO` (default), `DEBUG`, `WARNING` |
| `ALETHEIA_AUDIT_LOG_PATH` | Optional | Path to audit log file. Default: `audit.log` |
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | Recommended | Number of trusted proxy hops (0–5, default: 1). Set >1 behind load balancers. |
| `ALETHEIA_CORS_ORIGINS` | Optional | Comma-separated allowed CORS origins |
| `ALETHEIA_MANIFEST_KEY_VERSION` | Optional | Key version tag for manifest signing (default: `v1`) |

### Production checklist
- `ALETHEIA_MODE=active` — required in production, refuses shadow mode
- `ALETHEIA_RECEIPT_SECRET` — minimum 32 characters, required in active mode
- `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` — required for production (rate limiting, replay defense, decision store)
- `ALETHEIA_ALIAS_SALT` — strongly recommended, rotation predictable without it
- API keys — created via `POST /v1/keys` (KeyStore); `ALETHEIA_API_KEYS` env var is no longer supported
- Admin access — via RBAC permissions (OIDC/SAML bearer tokens); `X-Admin-Key` is no longer supported

---

## Persistent Disk Requirements

Aletheia Core requires writable paths for:

1. **Audit log** — `audit.log` (configurable via `ALETHEIA_AUDIT_LOG_PATH`)
2. **SQLite decision store** — `data/aletheia_decisions.sqlite3` (configurable via `ALETHEIA_DECISION_DB_PATH`; falls back to `$TMPDIR/aletheia/decisions.sqlite3` when not set)
3. **Anchor state** (proximity module only) — configurable via `ALETHEIA_ANCHOR_STATE_PATH`, requires `CONSCIOUSNESS_PROXIMITY_ENABLED=true`

For Render: use a persistent disk mounted at `/data` and set:

```
ALETHEIA_AUDIT_LOG_PATH=/data/audit.log
ALETHEIA_DECISION_DB_PATH=/data/decisions.sqlite3
```

### Multi-instance audit chain continuity

The audit hash-chain cursor resumes from the last persisted record at startup.
For horizontally scaled deployments, all instances must append to the same
append-only audit log backend (for example shared NFS volume, object-store append
pipeline on S3/GCS, or equivalent). Per-instance local files will create
independent chain segments and break global continuity guarantees.

---

## Manifest Signing Workflow

The security policy manifest must be signed before deployment.

```bash
# 1. Generate keypair (first time only — keys persist in manifest/)
python main.py sign-manifest

# 2. After editing manifest/security_policy.json:
python main.py sign-manifest

# 3. Commit both files:
git add manifest/security_policy.json manifest/security_policy.json.sig
git commit -m "chore: re-sign security manifest"
```

**Key rotation:**
```bash
# Delete old keys and re-generate
rm manifest/security_policy.ed25519.key manifest/security_policy.ed25519.pub
export ALETHEIA_MANIFEST_KEY_VERSION=v2
python main.py sign-manifest
# Update ALETHEIA_MANIFEST_KEY_VERSION=v2 in deployment env
```

---

## Startup Verification

On boot, Aletheia logs a self-check summary:

```
STARTUP SELF-CHECK: version=1.9.2 manifest=VALID expires_at=2027-03-07T00:00:00+00:00
  decision_store=upstash(connected) anchor_path=/data/anchor_state.json
  receipt_signing=enabled mode=active endpoints=[/health, /ready, /v1/audit]
```

Verify startup succeeded by checking:
1. No `FATAL:` log lines
2. Self-check shows `manifest=VALID`
3. `receipt_signing=enabled`
4. `decision_store` is not `degraded` (unless single-node)

---

## Health and Readiness Endpoints

### GET /health
Returns minimal status without auth. Extended diagnostics available to authenticated admin users.
Used by load balancers and uptime monitors.

```bash
curl https://your-app.onrender.com/health
```

Expected (public): `{"status": "ok", "service": "aletheia-core"}`

Admin diagnostics (requires RBAC admin role via Bearer token):

```bash
curl https://your-app.onrender.com/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Expected (admin): `{"status":"ok","service":"aletheia-core","version":"1.9.2",...}`

### GET /ready
Returns subsystem readiness: manifest, Redis, anchor, receipt signing.
Returns HTTP 200 when ready, HTTP 503 when degraded.

Also includes hosted demo diagnostics:
- `demo_key_configured`: demo key env var is present
- `demo_key_registered`: configured key exists in backend KeyStore
- `demo_key_status`: one of `not_configured`, `registered`, `missing`, `lookup_error`

```bash
curl https://your-app.onrender.com/ready
```

Expected: `{"ready": true, "manifest_signature": "VALID", ...}`

---

## Metrics Endpoint

### GET /metrics
Returns Prometheus/OpenMetrics-format metrics for scraping. No auth required.

```bash
curl https://your-app.onrender.com/metrics
```

Exported metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `aletheia_requests_total` | Counter | Total audit requests, labeled by `agent` and `verdict` |
| `aletheia_latency_seconds` | Histogram | Request processing latency |
| `aletheia_embedding_model_load_seconds` | Gauge | Time to load the embedding model at startup |
| `aletheia_keys_total` | Gauge | Number of active API keys |
| `aletheia_audit_log_bytes` | Counter | Total bytes written to the audit log |

Configure your Prometheus scrape config to target `/metrics` on your deployment host.

---

## Secret Rotation

### Hot rotation via API
```bash
curl -X POST https://your-app.onrender.com/v1/rotate \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Requires RBAC `SECRETS_ROTATE` permission. Returns HTTP 200 on success, HTTP 429 if called within the 10-second cooldown window.

On rotation:
- Reloads `ALETHEIA_RECEIPT_SECRET`, `ALETHEIA_ALIAS_SALT` from environment
- Re-verifies the manifest signature
- Rotates the Judge alias bank

### Hot rotation via signal
```bash
kill -SIGUSR1 $(pidof python)
```

Performs the same rotation without HTTP. The handler is installed at startup.

### Log rotation
Log rotation is configured in `deploy/logrotate.conf` for containerized deployments:
- Daily rotation, 30 days retention, compressed
- Max size: 100 MB per file
- Permissions: `0600` (owner read/write only)
- Signals uvicorn to reopen log files after rotation

### SQLite backups (development only)

> **Note:** Production deployments use Upstash Redis for the decision store.
> SQLite is only used for the API key store and local development.

`scripts/backup_sqlite.sh` provides hourly SQLite backups with integrity verification:
```bash
# Manual run
./scripts/backup_sqlite.sh /backups

# Cron (hourly)
0 * * * * /app/scripts/backup_sqlite.sh /backups
```
- Uses SQLite online backup API (safe with concurrent writers)
- Compresses backups with gzip
- Prunes backups older than `ALETHEIA_BACKUP_RETENTION_DAYS` (default: 7)
- Set `ALETHEIA_DB_PATH` to override the database path (default: `data/aletheia_decisions.sqlite3`)

---

## Degraded Mode

When `ready=false` or `fallback_state=degraded`:

- **Privileged actions are denied** (fail-closed). Only read-only operations proceed.
- **Audit receipts still work** if `ALETHEIA_RECEIPT_SECRET` is set.
- **Common causes:** Upstash Redis unreachable, manifest expired, bundle drift.

### How to resolve
1. Check `/ready` for which subsystem is degraded
2. If Redis: verify `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`
3. If manifest: re-sign with `python main.py sign-manifest` and redeploy
4. If bundle drift: redeploy all workers from the same commit

---

## Redis Outage Behavior

When Upstash Redis is unavailable:
- Decision store falls back to **SQLite** (local, single-node only)
- System enters **degraded mode** — privileged actions denied
- Read-only actions continue to work
- Replay defense operates locally (no cross-worker protection)

**Recovery:** Once Redis connectivity is restored, degraded mode clears on next request. Restart workers if state is stale.

---

## Replay Defense Behavior

- Each audit request generates a unique `request_id` (UUID) on the server.
- The decision token is derived as `SHA-256(request_id | timestamp_iso | policy_version | manifest_hash)`. The attacker cannot pre-compute a valid token without the server-issued `request_id`.
- Tokens are claimed via NX (set-if-not-exists) in Upstash Redis or SQLite `INSERT OR FAIL`. First claim wins.
- TTL: 1 hour (default). Expired tokens are pruned automatically.
- With Upstash Redis: replay defense is cross-worker. Without: local SQLite only (single-node protection).
- Bundle drift detection: on first request, policy version and manifest hash are registered. Subsequent requests from workers with a different policy version or manifest hash are rejected with `partial_deployment_drift`.

---

## Rollback Steps

### Quick rollback (Render)
1. Open Render dashboard → your service → Deploys
2. Click "Redeploy" on the last known-good deploy
3. Verify with: `curl https://your-app.onrender.com/health`

### Full rollback
```bash
git log --oneline -5          # Find last good commit
git revert HEAD               # Or: git reset --hard <commit>
git push origin main          # Trigger redeploy
```

### Rollback checklist
- [ ] Health endpoint returns `status: ok`
- [ ] Ready endpoint returns `ready: true`
- [ ] Smoke tests pass: `make smoke`
- [ ] No `FATAL:` lines in logs

---

## Self-Hosted Nginx Reference

A minimal reference config is provided at `deploy/nginx.conf` for self-hosted
operators using TLS termination and reverse proxying to Next.js + FastAPI.

The reference includes:
- HTTP to HTTPS redirect
- TLS termination with modern ciphers and session settings
- Security headers (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`)
- Upstream routing to FastAPI for `/v1/*`, `/health`, `/ready`, `/metrics`, and `/ws/audit`
- Upstream routing to Next.js for all other paths

Before production use:
- Replace certificate paths with your deployed certs
- Set `server_name` to your domain(s)
- Tune upstream host/ports for your process manager or container network

---

## Starlette Compatibility Validation

Compatibility validation for `starlette` was executed against:
- `0.46.2`
- `1.0.0`

Smoke/regression suite used for both runs:
- `tests/test_api.py`
- `tests/test_enterprise.py`
- `tests/test_redteam_adversarial.py`

Result: both versions passed (`156 passed`).

Pinned version: `starlette==1.0.0` in `requirements.in`.
