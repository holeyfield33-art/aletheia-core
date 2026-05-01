# Incident Response — Aletheia Core v1.9.2

Playbooks for common operational incidents. Each section includes
symptoms, diagnosis, and resolution steps.

---

## 1. Manifest Signature Failure

### Symptoms

- Service refuses to start with `ManifestTamperedError`
- `/ready` returns `manifest_signature: INVALID`
- Logs contain: `TAMPER DETECTED` or `Manifest signature verification failed`

### Causes

- `security_policy.json` was edited without re-signing
- Signature file (`security_policy.json.sig`) is missing or corrupted
- Public key was rotated but `ALETHEIA_MANIFEST_KEY_VERSION` was not updated
- Manifest has expired (`expires_at` is in the past)

### Resolution

```bash
# Re-sign the manifest
python main.py sign-manifest

# Verify locally
python -c "from manifest.signing import verify_manifest_signature; verify_manifest_signature('manifest/security_policy.json', 'manifest/security_policy.json.sig', 'manifest/security_policy.ed25519.pub')"

# Commit and redeploy
git add manifest/security_policy.json.sig
git commit -m "fix: re-sign security manifest"
git push
```

### If key was rotated

```bash
export ALETHEIA_MANIFEST_KEY_VERSION=v2  # or appropriate version
python main.py sign-manifest
# Update ALETHEIA_MANIFEST_KEY_VERSION in deployment environment
```

---

## 2. Redis / Upstash Down

### Symptoms

- `/ready` returns `decision_store_degraded: true`
- Privileged actions return HTTP 503 with `degraded_mode_privileged_action_denied`
- Logs contain: `Decision store bundle verification failure`
- Read-only operations still work

### Causes

- Upstash Redis service is down
- `UPSTASH_REDIS_REST_URL` or `UPSTASH_REDIS_REST_TOKEN` is incorrect
- Network connectivity issue between Render and Upstash

### Resolution

1. Check Upstash dashboard for service status
2. Verify env vars: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
3. Test connectivity:
   ```bash
   curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
        "$UPSTASH_REDIS_REST_URL/ping"
   ```
4. If Upstash is down: wait for recovery. System operates in degraded mode safely.
5. If env vars wrong: fix and restart the service.
6. After recovery: verify with `curl /ready` showing `decision_store_degraded: false`

### Acceptable degraded operation

- Single-node deployments with SQLite fallback are functional but lack cross-worker replay defense
- Read-only operations continue normally
- All privileged/write operations are denied (fail-closed)

---

## 3. Degraded Mode Appearing Unexpectedly

### Symptoms

- `/health` returns `fallback_state: degraded`
- `/ready` returns `ready: false`
- Privileged actions fail with 503

### Diagnosis

1. Check `/ready` for specific failed checks:
   - `manifest_signature: INVALID` → See Section 1
   - `manifest_expired: true` → Re-sign manifest with new `expires_at`
   - `decision_store_degraded: true` → See Section 2
   - `receipt_signing_configured: false` → Set `ALETHEIA_RECEIPT_SECRET`

2. Check logs for `FATAL:` or `ERROR:` entries
3. Check startup self-check summary in logs

### Resolution

Address the specific subsystem that is degraded per the `/ready` response.

---

## 4. Replay Rejection Spike

### Symptoms

- Many HTTP 409 responses with `reason: replay_detected`
- Spiky traffic patterns
- Clients receiving unexpected rejections

### Causes

- Client retrying with the same request without generating a new request
- Actual replay attack
- Redis key collision (extremely unlikely with SHA-256)
- Clock skew across workers

### Resolution

1. **If legitimate retries:** Client should not resubmit the exact same request body within the TTL window (1 hour). Each request should be unique.
2. **If attack:** The system is working correctly. Monitor source IPs and consider blocking at the load balancer.
3. **If clock skew:** Ensure all workers use NTP-synchronized clocks.
4. **Review logs:** Check `replay_token_outcome` field in audit logs to understand the pattern.

---

## 5. Receipt Signing Failure

### Symptoms

- Receipts contain `signature: UNSIGNED_DEV_MODE`
- Warning in receipt: `Set ALETHEIA_RECEIPT_SECRET for production receipt signing`
- Service refuses to start in active mode without receipt secret

### Causes

- `ALETHEIA_RECEIPT_SECRET` not set or too short (minimum 32 characters)
- Environment variable lost during deployment

### Resolution

```bash
# Generate a new secret
openssl rand -hex 32

# Set in deployment environment
# Render: Dashboard → Environment → ALETHEIA_RECEIPT_SECRET
# Docker: -e ALETHEIA_RECEIPT_SECRET=<generated_value>
```

**Important:** Changing the receipt secret invalidates all previously issued receipts.
Existing receipts will fail HMAC verification. This is expected and documented behavior.

---

## 6. Service Won't Start

### Symptoms

- Container exits immediately
- Logs show `FATAL:` messages

### Common causes and fixes

| Log message                                       | Cause                         | Fix                        |
| ------------------------------------------------- | ----------------------------- | -------------------------- |
| `ENVIRONMENT=production but ALETHEIA_MODE=shadow` | Shadow mode in prod           | Set `ALETHEIA_MODE=active` |
| `ALETHEIA_RECEIPT_SECRET is not set`              | Missing secret in active mode | Set the env var            |
| `ALETHEIA_RECEIPT_SECRET is too short`            | Secret < 32 chars             | Use `openssl rand -hex 32` |
| `ALETHEIA_API_KEYS is not set`                    | No API keys in active mode    | Set comma-separated keys   |
| `ManifestTamperedError`                           | Bad manifest/signature        | See Section 1              |

---

## Escalation

If none of the above resolve the issue:

1. Collect: startup logs, `/health` output, `/ready` output
2. Check recent commits for manifest or config changes
3. Rollback to last known-good deploy (see Operations Runbook)
4. Contact: info@aletheia-core.com with collected diagnostics
