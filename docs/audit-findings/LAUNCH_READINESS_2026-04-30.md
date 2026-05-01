# Aletheia Core — Launch Readiness Report

**Date:** 2026-04-30
**Audit reference:** docs/audit-findings/FINAL_AUDIT_REPORT_2026-04-30.md
**Fix reference:** docs/audit-findings/PHASED_FIX_PLAN_2026-04-30.md
**Prepared by:** Automated security & compliance audit pipeline

---

## Overall Verdict

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   VERDICT:   CONDITIONAL NO-GO                       ║
║                                                      ║
║   4 blocking items must be resolved before launch.   ║
║   Estimated remediation time: 3–5 business days.     ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## Blocking Items (must resolve before launch)

The following items represent either a security vulnerability that could be exploited
immediately, a data-leakage defect, or a test-suite failure that means the CI signal
cannot be trusted.

---

### BLOCK-1: Test suite does not verify production enforcement (BUG-01)

**Severity:** CRITICAL

`ALETHEIA_MODE=shadow` in `tests/conftest.py` means every DENIED decision is silently
converted to PROCEED in CI. The red-team, API-enforcement, and swarm tests all
**appear green** while the production enforcement code path is completely untested.

A regression to the Scout, Nitpicker, or Judge agents that breaks blocking would not
be caught by these tests.

**Resolution:** `PHASED_FIX_PLAN.md § P1-1` — estimated 2 hours.
**Launch gate:** CI must pass with `ALETHEIA_MODE=active` for all enforcement tests.

---

### BLOCK-2: `receipt.prompt` returns unredacted user payload (BUG-04)

**Severity:** HIGH — Data / Privacy

Every audit decision returns a JSON receipt containing a `prompt` field that holds the
raw, un-sanitised input payload. If the payload contains a user email address, phone
number, or account number, that PII is returned to the caller and would appear in any
client-side logs, browser history, or downstream system that stores the receipt.

**Resolution:** `PHASED_FIX_PLAN.md § P1-3` — estimated 30 minutes.
**Launch gate:** Automated test must assert no PII patterns survive in the receipt's `prompt` field.

---

### BLOCK-3: `hashKey()` crashes on missing `ALETHEIA_KEY_SALT` (BUG-02)

**Severity:** HIGH — Availability

A production deployment that omits `ALETHEIA_KEY_SALT` from the environment will throw
an unhandled exception the first time any user attempts to generate an API key. The error
propagates as a 500 with an unstructured response body. This is a likely deployment mistake
given that the variable is not yet documented as required.

**Resolution:** `PHASED_FIX_PLAN.md § P1-2` — estimated 30 minutes.
**Launch gate:** Key generation endpoint must return a structured error (not a thrown exception) when the salt is absent.

---

### BLOCK-4: Timing oracle on login unverified-email branch (BUG-03)

**Severity:** HIGH — Authentication / Account Enumeration

The login flow does not call `bcrypt.compare()` for accounts whose email is unverified,
and it does not call `recordLoginFailure()`. An attacker can distinguish verified from
unverified accounts by measuring response time. Unverified accounts also do not consume
rate-limit tokens, allowing unlimited probing.

**Resolution:** `PHASED_FIX_PLAN.md § P1-4` — estimated 1 hour.
**Launch gate:** Both branches must call `recordLoginFailure()` and both must execute a bcrypt comparison.

---

## Conditional Items (ship soon after launch)

These items do not block launch but must be scheduled for the first post-launch sprint.

| ID   | Title                                         | Target |
| ---- | --------------------------------------------- | ------ |
| P2-1 | IP-level aggregate rate limit on login        | Week 1 |
| P2-5 | `Permissions-Policy` header on API routes     | Week 1 |
| P2-4 | COOP / CORP headers                           | Week 1 |
| P2-6 | Centralised `clientFetch()` with 401 handling | Week 1 |
| P2-2 | Audit chain continuity across restarts        | Week 2 |
| P2-3 | CSP nonce replacing `unsafe-inline`           | Week 3 |
| P1-5 | Health endpoint passing in CI                 | Week 1 |
| P3-7 | Validate `starlette 1.0.0` compatibility      | Week 1 |

---

## Positive Signals

The following areas were reviewed and found to be in good shape. They do not require
action before launch.

| Area                        | Finding                                                                                                               |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Cryptographic binding       | Ed25519 manifest verification, HMAC-SHA256 receipts, timing-safe receipt verification — all correct.                  |
| Input hardening             | NFKC normalisation, zero-width stripping, recursive decode, confusable collapsing — complete.                         |
| Agent pipeline architecture | Three independent deny-capable agents; fail-closed on manifest tamper; replay defence; drift detection — all correct. |
| Injection resistance        | Pydantic `strict` + `extra="forbid"` on all inputs; Prisma parameterised queries; no raw SQL — clean.                 |
| Dependency integrity        | Python wheels hash-pinned via `pip-compile --generate-hashes`. Supply chain is strong.                                |
| Multi-tenant data isolation | All Prisma queries scoped by `userId`; no cross-tenant leakage pattern found.                                         |
| PII redaction in audit logs | `redact_pii()` applied before every audit log write.                                                                  |
| SSRF prevention             | Demo proxy enforces protocol and domain allowlist.                                                                    |
| Session security            | JWT `HttpOnly` cookie, 7-day `maxAge`, `secure` flag, `sameSite=lax`.                                                 |
| Audit retention             | 90-day policy documented; export endpoints present.                                                                   |
| Machine-verifiable receipts | HMAC receipt structure is technically verifiable; `/api/verify` endpoint available.                                   |

---

## Test Suite Summary

| Suite                         | Tests     | Passed            | Failed | Root Cause of Failures                          |
| ----------------------------- | --------- | ----------------- | ------ | ----------------------------------------------- |
| `test_api.py`                 | 34        | 29                | 5      | Shadow mode (3) + CI missing manifest/Redis (2) |
| `test_redteam_adversarial.py` | ~20       | ~17               | 3      | Shadow mode                                     |
| `test_swarm_1000bot.py`       | ~10       | ~9                | 1      | Shadow mode                                     |
| All other suites              | ~1 080    | ~1 064            | 0      | —                                               |
| **Total**                     | **1 144** | **1 119 (97.8%)** | **10** | **All trace to BLOCK-1**                        |

Fixing BLOCK-1 (§ P1-1) is expected to resolve all 10 failures.

---

## Go / No-Go Checklist

| #   | Item                                         | Status                                        |
| --- | -------------------------------------------- | --------------------------------------------- |
| 1   | CI passes with active-mode enforcement tests | ❌ Not met — shadow mode blocks this          |
| 2   | No PII in returned receipt                   | ❌ Not met — `receipt.prompt` raw             |
| 3   | Key generation works without crash           | ❌ Not met — throws on missing salt           |
| 4   | Login timing oracle closed                   | ❌ Not met — unverified branch missing bcrypt |
| 5   | Ed25519 manifest verified on every request   | ✅ Met                                        |
| 6   | Replay defence operational                   | ✅ Met                                        |
| 7   | Rate limiting functional (per-email)         | ✅ Met                                        |
| 8   | Audit log PII redaction                      | ✅ Met                                        |
| 9   | HMAC receipt scheme verifiable               | ✅ Met                                        |
| 10  | Input hardening applied                      | ✅ Met                                        |
| 11  | Supply chain integrity (hash-pinned)         | ✅ Met                                        |
| 12  | Multi-tenant isolation                       | ✅ Met                                        |
| 13  | SSRF protection                              | ✅ Met                                        |
| 14  | `ALETHEIA_KEY_SALT` documented as required   | ❌ Not met — see BLOCK-3                      |
| 15  | IP rate limit on login endpoint              | ⚠️ Post-launch (P2-1)                         |
| 16  | COOP/CORP headers                            | ⚠️ Post-launch (P2-4)                         |
| 17  | CSP without `unsafe-inline`                  | ⚠️ Post-launch (P2-3)                         |
| 18  | 401 session expiry handling in dashboard     | ⚠️ Post-launch (P2-6)                         |

**Go items:** 9/18 (items 5–13)
**Hard blockers (NO-GO):** 4 (items 1–4, 14)
**Conditional post-launch:** 4 (items 15–18)

---

## Remediation Sign-Off

Before changing this verdict to GO, the engineering lead must confirm:

- [ ] All four blocking items (BLOCK-1 through BLOCK-4) are merged to `main`.
- [ ] `pytest tests/test_api.py tests/test_redteam_adversarial.py tests/test_swarm_1000bot.py` passes with `ALETHEIA_MODE=active` in CI.
- [ ] `ALETHEIA_KEY_SALT` is listed as required in `docs/ENVIRONMENT_VARIABLES.md` and in the Render / Vercel deploy checklist.
- [ ] Automated receipt PII test is green.
- [ ] Post-launch items (P2-\*) are scheduled in the first sprint milestone.
