# Operations Runbook — Aletheia Core v1.6.0

This document covers day-to-day operations, environment setup, and troubleshooting
for a production Aletheia Core deployment.

---

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ALETHEIA_MODE` | Yes | `active` (production) / `shadow` (dev, log-only) / `monitor` |
| `ALETHEIA_RECEIPT_SECRET` | Yes (active) | HMAC signing secret for audit receipts. Generate: `openssl rand -hex 32` |
| `ALETHEIA_API_KEYS` | Yes (active) | Comma-separated API keys for `/v1/audit` authentication |
| `ALETHEIA_ALIAS_SALT` | Recommended | Salt for daily alias rotation. Generate: `openssl rand -hex 32` |
| `ALETHEIA_ANCHOR_STATE_PATH` | Recommended | Path for persistent replay token state (survives restarts) |
| `ALETHEIA_LOG_LEVEL` | Optional | `INFO` (default), `DEBUG`, `WARNING` |
| `UPSTASH_REDIS_REST_URL` | Optional | Upstash Redis URL for distributed replay defense |
| `UPSTASH_REDIS_REST_TOKEN` | Optional | Upstash Redis auth token |
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | Optional | Number of trusted proxy hops (default: 1) |
| `ALETHEIA_CORS_ORIGINS` | Optional | Comma-separated allowed CORS origins |
| `ALETHEIA_MANIFEST_KEY_VERSION` | Optional | Key version tag for manifest signing (default: `v1`) |

### Production checklist
- `ALETHEIA_MODE=active` — required in production, refuses shadow mode
- `ALETHEIA_RECEIPT_SECRET` — minimum 32 characters, required in active mode
- `ALETHEIA_API_KEYS` — at least one key, required in active mode
- `ALETHEIA_ALIAS_SALT` — strongly recommended, rotation predictable without it

---

## Persistent Disk Requirements

Aletheia Core requires writable paths for:

1. **Audit log** — `audit.log` (configurable via `ALETHEIA_AUDIT_LOG_PATH`)
2. **Anchor state** — `ALETHEIA_ANCHOR_STATE_PATH` for replay token persistence
3. **SQLite decision store** — `/tmp/aletheia_decisions.sqlite3` (fallback when Redis unavailable)

For Render: use a persistent disk mounted at `/data` and set:
```
ALETHEIA_ANCHOR_STATE_PATH=/data/anchor_state.json
ALETHEIA_AUDIT_LOG_PATH=/data/audit.log
```

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
STARTUP SELF-CHECK: version=1.6.0 manifest=VALID expires_at=2027-03-07T00:00:00+00:00
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
Returns service status, version, uptime. No auth required.
Used by load balancers and uptime monitors.

```bash
curl https://your-app.onrender.com/health
```

Expected: `{"status": "ok", "service": "aletheia-core", "version": "1.6.0", ...}`

### GET /ready
Returns subsystem readiness: manifest, Redis, anchor, receipt signing.
Returns HTTP 200 when ready, HTTP 503 when degraded.

```bash
curl https://your-app.onrender.com/ready
```

Expected: `{"ready": true, "manifest_signature": "VALID", ...}`

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

- Each audit request generates a unique `request_id` and `decision_token`
- Tokens are claimed via NX (set-if-not-exists) — first claim wins
- Duplicate claims return HTTP 409 with `reason: replay_detected`
- TTL: 1 hour (default). After expiry, the token can be reused.
- SQLite fallback: local replay defense only (no cross-worker protection)

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
