# Aletheia Core — Phased Fix Implementation Plan
**Date:** 2026-04-30
**Source:** docs/audit-findings/FINAL_AUDIT_REPORT_2026-04-30.md
**Owner:** Engineering lead

Each phase is self-contained and can be tracked as a milestone. Phases build on each
other; do not begin Phase 2 items that depend on Phase 1 infrastructure changes until
Phase 1 is merged and deployed.

---

## Phase 1 — Pre-Launch Blockers (target: ≤ 5 business days)

These items are **hard blockers**. Launch must not proceed until all are resolved and
verified in CI.

---

### P1-1: Fix shadow-mode test contamination (BUG-01)
**Priority:** CRITICAL
**Effort:** 2 h
**Files:** `tests/conftest.py`

**What to do:**
1. Remove `ALETHEIA_MODE=shadow` from the default pytest session fixture (`conftest.py` line 13).
2. Add two new fixtures:
   ```python
   @pytest.fixture()
   def active_mode_env(monkeypatch):
       monkeypatch.setenv("ALETHEIA_MODE", "active")

   @pytest.fixture()
   def shadow_mode_env(monkeypatch):
       monkeypatch.setenv("ALETHEIA_MODE", "shadow")
   ```
3. Update every test in `test_api.py`, `test_redteam_adversarial.py`, and
   `test_swarm_1000bot.py` that asserts a DENIED decision to use `active_mode_env`.
4. The two existing shadow-mode behavioural tests should use `shadow_mode_env`.
5. Re-run the full suite; confirm 0 failures in the enforcement test files.

**Acceptance criteria:** `pytest tests/test_api.py tests/test_redteam_adversarial.py tests/test_swarm_1000bot.py` — 0 failures, enforcements tests all green.

---

### P1-2: Guard `hashKey()` against missing `ALETHEIA_KEY_SALT` (BUG-02)
**Priority:** HIGH
**Effort:** 30 min
**Files:** `app/api/keys/route.ts`

**What to do:**
1. At the top of the `POST` handler in `app/api/keys/route.ts`, add an environment guard:
   ```ts
   if (!process.env.ALETHEIA_KEY_SALT) {
     return NextResponse.json(
       { error: "Server configuration error. Contact support." },
       { status: 500 }
     );
   }
   ```
2. Add `ALETHEIA_KEY_SALT` to `docs/ENVIRONMENT_VARIABLES.md` as a **required** variable
   and to the Render / Vercel onboarding checklist.
3. Add a test that mocks the env var as absent and asserts a 500 with a safe error message
   (no stack trace in response body).

**Acceptance criteria:** Key generation endpoint returns structured `{"error": "..."}` (not a thrown exception trace) when the salt is absent.

---

### P1-3: Redact PII from `receipt.prompt` (BUG-04)
**Priority:** HIGH
**Effort:** 30 min
**Files:** `core/audit.py`

**What to do:**
1. Locate the call to `build_tmr_receipt(prompt=payload)` (line 346).
2. Change it to `build_tmr_receipt(prompt=redact_pii(payload))`.
3. Ensure `redact_pii` is imported at the call site (it is already defined in the same file).
4. Add a test: submit a payload containing `user@example.com`; assert the receipt returned
   does not contain `user@example.com`.

**Acceptance criteria:** No email/phone/SSN patterns survive in any returned receipt's `prompt` field.

---

### P1-4: Fix timing oracle in login unverified-email branch (BUG-03)
**Priority:** HIGH
**Effort:** 1 h
**Files:** `lib/auth.ts`

**What to do:**
1. In the `!user.emailVerified` branch, call `await bcrypt.compare(password, user.passwordHash)`
   (using the hash from the DB, even though the result is discarded) before returning the
   "Email not verified" error. This equalises timing between the verified and unverified paths.
2. After the (discarded) bcrypt call, call `recordLoginFailure(email)`.
3. Add a test that measures the p95 response time for both branches and asserts they are
   within 50 ms of each other (or use a simpler mock-timing assertion if test environment
   does not support wall-clock measurement).

**Acceptance criteria:** Both `emailVerified=true` (wrong password) and `emailVerified=false` paths call `recordLoginFailure()` and undergo a bcrypt comparison.

---

### P1-5: Fix CI health endpoint (BUG-07)
**Priority:** MEDIUM (unblocks CI trustworthiness)
**Effort:** 1 h
**Files:** `bridge/fastapi_wrapper.py`, `tests/conftest.py`

**What to do:**
1. Add a `ALETHEIA_SKIP_MANIFEST_CHECK=true` environment variable that, when set, causes
   the readiness endpoint to skip the Ed25519 manifest verification and Redis ping.
2. Set this variable in the pytest session fixture for the health-endpoint tests only.
3. Alternatively: add a dedicated `TestHealthUnit` that mocks the manifest load and Redis
   client.

**Acceptance criteria:** `test_health_readiness_*` tests pass without a real Redis or manifest in the test environment.

---

## Phase 2 — High-Priority Post-Launch Hardening (target: week 1–4 post-launch)

These items are important for security posture and production reliability but do not block the initial launch once Phase 1 is complete.

---

### P2-1: Add IP-level aggregate rate limit on login endpoint
**Priority:** HIGH
**Effort:** 2 h
**Files:** `app/api/auth/[...nextauth]/route.ts`, `lib/rate-limit.ts`

**What to do:**
Add a second rate-limit check keyed on `req.ip` (or `x-forwarded-for` header) in addition
to the existing per-email check. Limit: 20 attempts per IP per 15-minute window. Use the
existing `consumeRateLimit` / UpstashRateLimiter infrastructure.

---

### P2-2: Audit chain continuity across restarts (BUG-05)
**Priority:** MEDIUM
**Effort:** 3 h
**Files:** `core/audit.py`

**What to do:**
1. On module init, read the last entry from the persisted audit log and seed the chain with
   its hash instead of `"GENESIS"`.
2. If no log entries exist, fall back to `"GENESIS"`.
3. For multi-instance deployments, document that a shared append-only log (S3 / GCS / NFS)
   is required for chain continuity.

---

### P2-3: Replace `unsafe-inline` CSP with nonce-based policy
**Priority:** MEDIUM
**Effort:** 4 h
**Files:** `middleware.ts`, `app/layout.tsx`

**What to do:**
Generate a per-request nonce in `middleware.ts`, attach it to the response header, and
pass it to `<Script nonce={nonce}>` via the [`headers()` API](https://nextjs.org/docs/app/api-reference/functions/headers).
Replace `'unsafe-inline'` with `'nonce-{nonce}'` and `'strict-dynamic'`.

---

### P2-4: Add COOP and CORP headers (OWASP A05)
**Priority:** MEDIUM
**Effort:** 30 min
**Files:** `middleware.ts`

**What to do:**
```ts
res.headers.set("Cross-Origin-Opener-Policy", "same-origin");
res.headers.set("Cross-Origin-Resource-Policy", "same-origin");
```

---

### P2-5: Move `Permissions-Policy` to middleware response (OWASP A05)
**Priority:** LOW
**Effort:** 30 min
**Files:** `middleware.ts`

**What to do:**
Copy the `Permissions-Policy` header value from `next.config.js` into the
`middleware.ts` response object so it is present on API-route responses as well.

---

### P2-6: Create `lib/client-fetch.ts` with 401 handling (RF-02)
**Priority:** HIGH
**Effort:** 3 h
**Files:** `lib/client-fetch.ts` (new), all `app/dashboard/**` components

**What to do:**
1. Create `lib/client-fetch.ts`:
   ```ts
   export async function clientFetch<T>(
     url: string,
     init?: RequestInit,
     timeoutMs = 10_000
   ): Promise<T> {
     const controller = new AbortController();
     const timer = setTimeout(() => controller.abort(), timeoutMs);
     try {
       const res = await fetch(url, { ...init, signal: controller.signal });
       if (res.status === 401) {
         await signOut({ callbackUrl: "/login" });
         throw new Error("Session expired");
       }
       if (!res.ok) throw new Error(`HTTP ${res.status}`);
       return res.json() as Promise<T>;
     } finally {
       clearTimeout(timer);
     }
   }
   ```
2. Replace all 11 bare `fetch()` calls in `app/dashboard/**` with `clientFetch()`.

---

### P2-7: Add HSTS `preload` directive
**Priority:** LOW
**Effort:** 15 min
**Files:** `middleware.ts`

**What to do:**
Append `; preload` to the `Strict-Transport-Security` header value. Submit the domain to
the HSTS preload list only after confirming all subdomains serve valid HTTPS.

---

## Phase 3 — Tech Debt and Long-Term Hardening (target: month 2+)

---

### P3-1: Add `<label>` to demo textarea (A11Y-01)
**Priority:** LOW
**Files:** `app/demo/page.tsx`

Add a visible or visually-hidden `<label htmlFor="payload-input">Audit payload</label>`
above the demo textarea. Remove the placeholder text as the sole labelling mechanism.

---

### P3-2: Add `aria-live` region to audit log table (A11Y-02)
**Priority:** LOW
**Files:** `app/dashboard/DashboardOverview.tsx` (or dedicated audit log component)

Wrap the audit log table update trigger in an `aria-live="polite"` region so screen
readers announce new rows.

---

### P3-3: Extract `lib/pipeline-client.ts` refactoring (RF-05)
**Priority:** LOW
**Files:** `bridge/fastapi_wrapper.py`

Extract `_run_scout()`, `_run_nitpicker()`, `_run_judge()` helper functions from the
monolithic `handle_request()` function to improve readability and allow isolated unit
testing of pipeline stages.

---

### P3-4: Replace `print()` with structured logging in `economics/` (RF-04)
**Priority:** LOW
**Files:** `economics/*.py`

Replace bare `print()` calls with `logging.getLogger(__name__).debug(...)`.

---

### P3-5: Lock npm packages with exact versions for security-sensitive deps
**Priority:** MEDIUM
**Files:** `package.json`

Change `next-auth`, `bcryptjs`, and `@prisma/client` to exact version pins
(`"next-auth": "4.24.13"`) and commit `package-lock.json`. Automate updates via
Dependabot or Renovate.

---

### P3-6: Add Nginx reference configuration for self-hosted operators
**Priority:** LOW
**Files:** `docs/OPERATIONS_RUNBOOK.md` or `deploy/nginx.conf` (new)

Provide a minimal commented `nginx.conf` illustrating TLS termination, security headers,
and upstream proxy configuration to the FastAPI and Next.js processes.

---

### P3-7: Validate `starlette 1.0.0` compatibility
**Priority:** MEDIUM
**Files:** `requirements.in`

Run the full test suite and integration smoke tests against `starlette 0.46.x` (previous
stable) and `starlette 1.0.0`. Document any breaking changes encountered and pin to the
validated version.

---

## Fix Tracking Summary

| ID | Severity | Phase | Effort | Owner |
|----|----------|-------|--------|-------|
| P1-1 | CRITICAL | 1 | 2 h | — |
| P1-2 | HIGH | 1 | 0.5 h | — |
| P1-3 | HIGH | 1 | 0.5 h | — |
| P1-4 | HIGH | 1 | 1 h | — |
| P1-5 | MEDIUM | 1 | 1 h | — |
| P2-1 | HIGH | 2 | 2 h | — |
| P2-2 | MEDIUM | 2 | 3 h | — |
| P2-3 | MEDIUM | 2 | 4 h | — |
| P2-4 | MEDIUM | 2 | 0.5 h | — |
| P2-5 | LOW | 2 | 0.5 h | — |
| P2-6 | HIGH | 2 | 3 h | — |
| P2-7 | LOW | 2 | 0.25 h | — |
| P3-1 | LOW | 3 | 0.5 h | — |
| P3-2 | LOW | 3 | 1 h | — |
| P3-3 | LOW | 3 | 2 h | — |
| P3-4 | LOW | 3 | 0.5 h | — |
| P3-5 | MEDIUM | 3 | 1 h | — |
| P3-6 | LOW | 3 | 1 h | — |
| P3-7 | MEDIUM | 3 | 2 h | — |

**Phase 1 total effort estimate:** ~5 hours
**Phase 2 total effort estimate:** ~14 hours
**Phase 3 total effort estimate:** ~8 hours
**Grand total:** ~27 engineer-hours
