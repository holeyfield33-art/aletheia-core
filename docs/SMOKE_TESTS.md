# Smoke Tests — Aletheia Core v1.9.2

Live post-deploy verification against a running Aletheia Core backend.

---

## Pre-Launch Wiring Smoke Test

Run in incognito tab. Stop and document any failure.

### Anonymous user
- [ ] Land on `/` -- homepage renders, no console errors
- [ ] Click every footer link -- all 7 legal links resolve to a page
- [ ] Click "Demo" in nav -- `/demo` loads
- [ ] Click "Pricing" in nav -- `/pricing` loads
- [ ] On pricing page, click "Start Free" -- lands on `/dashboard/keys` (or login redirect)
- [ ] Click "Contact for Enterprise" -- opens email client (mailto)
- [ ] Click "GitHub" external link -- opens repo in new tab
- [ ] Footer "Status" link -- `/status` loads

### New user signup
- [ ] Click "Sign up" -- `/auth/register` loads
- [ ] Submit without ToS check -- error shown
- [ ] Submit with ToS check -- success, redirected to `/auth/verify-email` or `/onboarding`
- [ ] Email verification link works
- [ ] Onboarding flow completes and redirects to `/dashboard`
- [ ] Dashboard shows zero state correctly (no API keys yet)

### API key generation
- [ ] `/dashboard/keys` -- "Create API Key" button visible
- [ ] Click "Create API Key" -- modal/form opens
- [ ] Submit name -- key generated, full key shown ONCE with copy button
- [ ] Copy button copies to clipboard (verify with paste)
- [ ] Reload page -- key prefix visible, full key NOT visible (proves one-time display)
- [ ] Click "Revoke" -- confirmation, key marked revoked

### First API call
- [ ] Use generated key in curl against `/v1/audit` endpoint
- [ ] Returns 200 with `decision`, `request_id`, `receipt`, `metadata` (post-Phase-1 contract)
- [ ] Returns again with rate-limit-aware behavior on burst

### Dashboard data flow (post-Phase-2)
- [ ] `/dashboard` -- Total Requests counter > 0 after curl
- [ ] `/dashboard` -- Audit Decisions counter > 0
- [ ] `/dashboard/logs` -- row appears for the curl request
- [ ] **Click the row -- detail panel opens with full receipt** (Task 1 wiring)
- [ ] Click "Copy request_id" -- value copied
- [ ] Click "Copy receipt" -- JSON copied
- [ ] `/dashboard/usage` -- accurate request count for this key
- [ ] `/dashboard/policy` -- active manifest displays
- [ ] `/dashboard/evidence` -- JSONL export downloads, contains the receipt

### Tenancy isolation (manual probe)
- [ ] Sign up a second user in a different incognito window
- [ ] User B's dashboard shows zero records
- [ ] User B cannot see User A's logs, keys, or receipts
- [ ] Generate a key as User B, hit `/v1/audit`, confirm User A's counters do not change

### Settings and account
- [ ] `/dashboard/settings` -- name editable, save works
- [ ] "Export account data" -- JSONL of user's data downloads
- [ ] "Delete account" -- confirmation flow works (do this last on a test user)

### Stripe (use Stripe test mode keys)
- [ ] Pricing -> "Upgrade Hosted Plan" -- Stripe checkout opens
- [ ] Use test card 4242 4242 4242 4242 -- checkout completes
- [ ] Redirected to `/dashboard?upgraded=true`
- [ ] User plan field updates within 60 seconds (webhook fired)
- [ ] Audit log retention extended per new plan

---

## Prerequisites

- Python 3.10+
- `httpx` installed (`pip install httpx`)
- A deployed Aletheia Core instance
- A valid API key (if auth is enabled)

---

## How to Run

```bash
# Set target and credentials
export ALETHEIA_BASE_URL=https://your-app.onrender.com
export ALETHEIA_API_KEY=your-api-key

# Run smoke tests
python scripts/smoke_test_live.py

# Or via Make
make smoke
```

---

## What Gets Tested

| #   | Test                   | Path              | Expected                                               |
| --- | ---------------------- | ----------------- | ------------------------------------------------------ |
| 1   | Health endpoint        | GET /health       | 200, status=ok                                         |
| 2   | Readiness endpoint     | GET /ready        | 200 or 503 with ready field                            |
| 3   | Benign summarize       | POST /v1/audit    | decision=PROCEED                                       |
| 4   | Prompt injection       | POST /v1/audit    | decision=DENIED                                        |
| 5   | Destructive execution  | POST /v1/audit    | decision=DENIED or SANDBOX_BLOCKED                     |
| 6   | Replay defense         | POST /v1/audit ×2 | Both handled without crash                             |
| 7   | Unknown extra field    | POST /v1/audit    | 422 (Pydantic extra=forbid)                            |
| 8   | Oversized input        | POST /v1/audit    | 422 (max_length exceeded)                              |
| 9   | Receipt fields         | POST /v1/audit    | receipt contains decision, policy_hash, signature      |
| 10  | Security headers       | GET /health       | Cache-Control, X-Content-Type-Options, X-Frame-Options |
| 11  | Method not allowed     | GET /v1/audit     | 405                                                    |
| 12  | Unauthorized tool call | POST /v1/audit    | decision=DENIED or SANDBOX_BLOCKED                     |

---

## Expected Output

```
============================================================
ALETHEIA CORE — LIVE SMOKE TEST
Target: https://your-app.onrender.com
============================================================

  [PASS] health_endpoint — status=ok code=200
  [PASS] readiness_endpoint — ready=True code=200
  [PASS] benign_summarize — decision=PROCEED code=200
  [PASS] prompt_injection_denied — decision=DENIED code=403
  [PASS] destructive_execution_denied — decision=SANDBOX_BLOCKED code=403
  [PASS] replay_defense — r1=200 r2=200
  [PASS] unknown_extra_field_rejected — code=422
  [PASS] oversized_input_rejected — code=422
  [PASS] receipt_fields_present — decision=PROCEED
  [PASS] security_headers — all present
  [PASS] method_not_allowed_405 — GET /v1/audit → 405
  [PASS] unauthorized_tool_call_denied — decision=DENIED code=403

============================================================
RESULTS: 12/12 passed, 0 failed
============================================================
```

---

## What Blocks Launch

Any failure in the following tests **must be resolved before launch**:

1. **health_endpoint** — service is not running or not responding
2. **benign_summarize** — legitimate requests are being incorrectly blocked
3. **prompt_injection_denied** — security pipeline is not blocking attacks
4. **receipt_fields_present** — audit trail integrity is broken
5. **security_headers** — response hardening is missing

Failures in readiness or replay defense may indicate degraded mode, which
is acceptable for initial launch on single-node deployments but should be
resolved before scaling.

---

## Manual Verification (Not Automated)

### Degraded mode for privileged actions

1. Temporarily remove `UPSTASH_REDIS_REST_URL` from env
2. Restart the service
3. Send a privileged action: `action=Transfer_Funds`
4. Verify: HTTP 503, `decision=DENIED`, `reason=degraded_mode_privileged_action_denied`
5. Restore Redis env and restart
