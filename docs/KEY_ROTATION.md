# Key Rotation Runbook — Aletheia Core v1.9.2

Step-by-step procedure for rotating Ed25519 manifest signing keys and
runtime secrets in production.

---

## Prerequisites

| Item | Details |
|------|---------|
| Python 3.10+ with `cryptography` installed | Required for key generation and signing |
| Access to the private signing key | Stored offline — never on production hosts |
| Deployment pipeline that can publish files to all instances | Public key + signature must land atomically |

---

## 1. Rotate Ed25519 Manifest Signing Key

Use this procedure when the Ed25519 private key is compromised, expired by
organisational policy, or being rotated on schedule.

### 1.1 Generate a New Keypair (offline machine)

```bash
cd aletheia-core

# Generate new keypair — private key is chmod 0600 automatically
python -c "
from manifest.signing import generate_keypair
generate_keypair(
    private_key_path='manifest/security_policy.ed25519.key',
    public_key_path='manifest/security_policy.ed25519.pub',
)
print('Keypair generated.')
"
```

Output files:
- `manifest/security_policy.ed25519.key` — **NEVER deploy this file**
- `manifest/security_policy.ed25519.pub` — deploy to all instances

### 1.2 Re-sign the Manifest

```bash
python -c "
from manifest.signing import sign_manifest
sign_manifest(
    manifest_path='manifest/security_policy.json',
    signature_path='manifest/security_policy.json.sig',
    private_key_path='manifest/security_policy.ed25519.key',
    public_key_path='manifest/security_policy.ed25519.pub',
)
print('Manifest signed.')
"
```

Output files:
- `manifest/security_policy.json.sig` — deploy to all instances

### 1.3 Bump the Key Version

Set the `ALETHEIA_MANIFEST_KEY_VERSION` environment variable on **all** instances
to match the version embedded in the new signature. Default is `"v1"`.

```bash
# Example: bump to v2
export ALETHEIA_MANIFEST_KEY_VERSION=v2
```

> **Warning:** If any instance has a mismatched key version, the Judge will raise
> `ManifestTamperedError` and hard-deny all requests.

### 1.4 Deploy

1. Commit the new `.pub` and `.sig` files to version control.
2. **Do NOT commit the private key.** Verify `.gitignore` excludes `*.key`.
3. Deploy all instances simultaneously. Partial rollout (some old key, some new)
   triggers bundle drift rejection.
4. Verify deployment:

```bash
# On each instance
curl -s https://YOUR_HOST/health | jq .
# Expected: {"status": "ok", ...}

curl -s https://YOUR_HOST/ready | jq .
# Expected: {"ready": true, "manifest_ok": true, ...}
```

### 1.5 Roll Back (if needed)

If the new key/signature causes failures:

1. Redeploy the **previous** `.pub` and `.sig` files.
2. Revert `ALETHEIA_MANIFEST_KEY_VERSION` to the previous value.
3. Restart all instances.
4. Re-sign with corrected keys at your next opportunity.

There is no automatic rollback. `ManifestTamperedError` is a hard failure — the
Judge blocks **all** actions until the manifest verifies successfully.

---

## 2. Re-sign the Manifest (same key)

Use this when the manifest JSON has been updated (new restricted actions, expiry
extension, etc.) but the signing key is unchanged.

```bash
# On the offline signing machine
python -c "
from manifest.signing import sign_manifest
sign_manifest(
    manifest_path='manifest/security_policy.json',
    signature_path='manifest/security_policy.json.sig',
    private_key_path='manifest/security_policy.ed25519.key',
    public_key_path='manifest/security_policy.ed25519.pub',
)
"
```

Deploy the updated `security_policy.json` **and** `security_policy.json.sig`
together. Deploying only one will fail signature verification.

### Manifest Expiry

The Judge enforces `expires_at` from the manifest. Expired manifests enter a
**7-day grace period** (warning logged). After the grace window, all requests
are hard-denied. Re-sign with an updated `expires_at` before the grace window
closes.

Current manifest expiry: `2027-03-07T00:00:00+00:00`

---

## 3. Rotate Runtime Secrets

Runtime secrets are environment variables that can be rotated without
restarting the process.

### 3.1 Secrets That Can Be Rotated

| Secret | Env Var | Purpose |
|--------|---------|---------|
| Receipt signing | `ALETHEIA_RECEIPT_SECRET` | HMAC-SHA256 audit receipt signatures |
| API keys | `ALETHEIA_API_KEYS` | Comma-separated list of valid client keys |
| Alias salt | `ALETHEIA_ALIAS_SALT` | Daily alias bank rotation seed |
| Admin key | `ALETHEIA_ADMIN_KEY` | Admin endpoint authentication |

### 3.2 Update Environment Variables

Update the secrets in your deployment platform (Render dashboard, Kubernetes
secrets, Docker Compose `.env`, etc.).

### 3.3 Trigger Rotation

**Option A — HTTP endpoint (preferred):**

```bash
curl -X POST https://YOUR_HOST/v1/rotate \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

Expected response:
```json
{
  "status": "rotated",
  "receipt_secret": true,
  "api_keys_count": 3,
  "alias_salt": true,
  "admin_key": true
}
```

**Option B — POSIX signal:**

```bash
kill -SIGUSR1 $(pgrep -f "uvicorn bridge.fastapi_wrapper")
```

### 3.4 Safety Mechanisms

- **Thread lock:** Rotation is serialised — no torn state during reload.
- **10-second cooldown:** Back-to-back rotation requests return `{"status": "cooldown"}`.
- **Audit trail:** Every rotation is logged with a summary (no secret values exposed).
- **Manifest re-verification:** Rotation also re-verifies the Ed25519 manifest
  signature and refreshes the Judge's daily alias bank.

### 3.5 Impact of Secret Rotation

| Secret | Impact When Rotated |
|--------|---------------------|
| `ALETHEIA_RECEIPT_SECRET` | New receipts use new key. Old receipts verify against old key (unless old key is no longer available for verification). |
| `ALETHEIA_API_KEYS` | Old keys stop working immediately. Distribute new keys to clients first. |
| `ALETHEIA_ALIAS_SALT` | Daily alias bank shuffle changes. May alter veto behavior for grey-zone payloads. |
| `ALETHEIA_ADMIN_KEY` | Previous admin key stops working. Update your ops tooling. |

---

## 4. Verification Checklist

After any rotation:

- [ ] `/health` returns `{"status": "ok"}`
- [ ] `/ready` returns `{"ready": true, "manifest_ok": true}`
- [ ] Test audit request returns a valid PROCEED/DENIED decision
- [ ] Prometheus metrics at `/metrics` show `aletheia_requests_total` incrementing
- [ ] Audit log has a rotation event (check `ALETHEIA_AUDIT_LOG_PATH`)
- [ ] No `ManifestTamperedError` in application logs

---

## 5. Emergency Procedures

### Manifest Verification Failure in Production

1. Check `/ready` — `manifest_ok` will be `false`.
2. Verify that `security_policy.json`, `security_policy.json.sig`, and
   `security_policy.ed25519.pub` are all present and from the same signing.
3. Check `ALETHEIA_MANIFEST_KEY_VERSION` matches the `key_version` in the `.sig` file.
4. If mismatch, redeploy the correct file set or revert to the last known-good version.

### Lost Private Key

1. Generate a new keypair (Section 1.1).
2. Re-sign the manifest (Section 1.2).
3. Deploy new `.pub` and `.sig`.
4. Destroy any copies of the compromised key.
5. Update internal key management records.
