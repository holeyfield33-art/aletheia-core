# Smoke Tests — Aletheia Core v1.6.2

Live post-deploy verification against a running Aletheia Core backend.

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

| # | Test | Path | Expected |
|---|------|------|----------|
| 1 | Health endpoint | GET /health | 200, status=ok |
| 2 | Readiness endpoint | GET /ready | 200 or 503 with ready field |
| 3 | Benign summarize | POST /v1/audit | decision=PROCEED |
| 4 | Prompt injection | POST /v1/audit | decision=DENIED |
| 5 | Destructive execution | POST /v1/audit | decision=DENIED or SANDBOX_BLOCKED |
| 6 | Replay defense | POST /v1/audit ×2 | Both handled without crash |
| 7 | Unknown extra field | POST /v1/audit | 422 (Pydantic extra=forbid) |
| 8 | Oversized input | POST /v1/audit | 422 (max_length exceeded) |
| 9 | Receipt fields | POST /v1/audit | receipt contains decision, policy_hash, signature |
| 10 | Security headers | GET /health | Cache-Control, X-Content-Type-Options, X-Frame-Options |
| 11 | Method not allowed | GET /v1/audit | 405 |

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

============================================================
RESULTS: 11/11 passed, 0 failed
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
