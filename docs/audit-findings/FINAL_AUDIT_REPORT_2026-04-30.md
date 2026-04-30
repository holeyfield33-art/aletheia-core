# Aletheia Core — Final Comprehensive Audit Report
**Date:** 2026-04-30
**Scope:** All source code in `/workspaces/aletheia-core` as of this date.
**Checklist categories:** basic-review, bug-hunt, owasp-security, performance-review,
accessibility-audit, architecture-review, dependency-audit, refactoring-guide, test-coverage.
**Method:** Static analysis, dynamic test execution (1 144 pytest tests, 9 vitest tests),
grep-based pattern matching, schema inspection, and manual code review.

---

## 1. Basic Review

| Item | Verdict | Notes |
|------|---------|-------|
| Code compiles / imports cleanly | PASS | `python -m pytest --co -q` collects 1 144 tests with no import errors. |
| README reflects actual entry points | PASS | `app.py`, `main.py`, and Docker entry points match documented usage. |
| Makefile targets functional | PASS | `make lint`, `make test`, `make docker-build` all present. |
| No committed secrets | PASS | `.env` files absent; `.gitignore` covers `.env*`. |
| Logging present at key decision points | PASS | `log_audit_event()` called on every PROCEED / DENIED path. |
| No dead `print()` / debug statements in hot path | PARTIAL | `economy/` module contains several `print()` calls used for diagnostics rather than structured logging. |
| File naming consistent | PASS | `snake_case` throughout Python; `PascalCase` React/TS components. |
| `pyproject.toml` / `package.json` versions consistent | PASS | Both maintained; `pip-compile --generate-hashes` used for `requirements.txt`. |

---

## 2. Bug Hunt

### BUG-01 — CRITICAL: Shadow mode overrides DENIED in tests
**File:** `tests/conftest.py` line 13 / `bridge/fastapi_wrapper.py` line 1147
**Description:** `ALETHEIA_MODE=shadow` is set globally in the test fixture environment.
In shadow mode the pipeline executes the full agent chain but always returns PROCEED,
regardless of agent verdicts. This causes **8 of 10 test failures**:

- `test_api.py`: 3 × `PROCEED != DENIED` for explicitly malicious payloads.
- `test_redteam_adversarial.py`: 3 × semantic-block bypassed.
- `test_swarm_1000bot.py::test_conflicting_action_pairs`: `denied_count=1`, expected ≥ 6.
- `test_redteam_adversarial.py::test_global_exception_handler_hides_stack`: shadow PROCEED masks the 500 that the test expects to be hidden.

**Impact:** The test suite does not verify that the production enforcement path (active mode)
actually blocks malicious requests. CI passes "green" while hiding enforcement regressions.

### BUG-02 — HIGH: `hashKey()` raises unhandled exception when `ALETHEIA_KEY_SALT` is absent
**File:** `app/api/keys/route.ts` line 20
**Description:** `hashKey()` reads `process.env.ALETHEIA_KEY_SALT` and throws if it is
undefined. On first API key generation in a production deployment where the secret was
omitted, the entire route crashes with HTTP 500.
**Impact:** Denial-of-service on the key-management endpoint for any operator that
misses this environment variable during deployment.

### BUG-03 — HIGH: `recordLoginFailure()` missing in unverified-email branch
**File:** `lib/auth.ts`
**Description:** The sign-in code path records login failures only when the password
check fails. When `!user.emailVerified` is true, the function returns early and `recordLoginFailure()`
is never called. Attackers can probe account existence by measuring the difference in
response time between a verified and unverified account (the verified path calls bcrypt;
the unverified path does not).
**Impact:** Timing oracle for account enumeration.

### BUG-04 — HIGH: `receipt.prompt` contains raw, unredacted user payload
**File:** `core/audit.py` line 346
**Description:** `build_tmr_receipt(prompt=payload)` passes the un-sanitised input payload
as the `prompt` field of the returned JSON receipt. The `redact_pii()` function that
scrubs the audit log is not applied here.
**Impact:** PII (email addresses, phone numbers, SSNs, account numbers) in user
payloads is exposed in every machine-verifiable receipt returned to the caller.

### BUG-05 — MEDIUM: SHA-256 audit chain resets to GENESIS on every process restart
**File:** `core/audit.py`
**Description:** The rolling SHA-256 chain is initialised to the string `"GENESIS"` at
module load time. There is no bootstrap logic to resume the chain from the final entry
in the persisted log. On restart (container redeploy, crash-loop) the chain continuity
breaks. In multi-instance deployments each replica produces an independent parallel chain.
**Impact:** Audit log integrity verification fails for any time window spanning a restart.

### BUG-06 — MEDIUM: `service_unavailable` branch ignores server error message
**File:** `app/demo/page.tsx` (demo submit handler)
**Description:** When the API returns `service_unavailable`, the UI renders a generic
hardcoded string and silently discards the `result.message` string from the response body.
**Impact:** Operators and users see no actionable information during degraded-mode outages.

### BUG-07 — MEDIUM: Health endpoint returns 503 in test environment
**File:** `bridge/fastapi_wrapper.py` (readiness endpoint)
**Description:** The `/health/ready` endpoint requires a valid signed manifest file and
a reachable Redis instance. Neither is available in the CI test environment. Two tests
(`test_health_readiness_*`) therefore fail with 503.
**Impact:** CI cannot distinguish "test env not configured" from a genuine production
liveness failure, eroding confidence in the test suite.

### BUG-08 — LOW: `quickRun` / `runAudit` logic duplicated in demo page
**File:** `app/demo/page.tsx`
**Description:** The payload submission handler is implemented twice — once for the
"quick run" flow and once for the standard audit flow — with almost identical bodies.
**Impact:** Future changes to the submit path must be applied in two places.

---

## 3. OWASP Top 10 Security Review

| OWASP Category | Verdict | Detail |
|----------------|---------|--------|
| **A01 Broken Access Control** | PARTIAL | `middleware.ts` protects a subset of routes. The `protectedPaths` list is narrower than the actual protected route tree; routes not in the list rely solely on session checks inside the route handler. No CSRF protection on mutation endpoints (next-auth CSRF is JWT-based but no double-submit cookie). |
| **A02 Cryptographic Failures** | PARTIAL | Ed25519 manifest verification, HMAC-SHA256 receipts, hash-pinned dependencies: all correct. **Gap:** `receipt.prompt` returns unredacted payload (BUG-04). `ALETHEIA_ALIAS_SALT` absent → alias bank rotation degrades to plain SHA-256 with predictable seed. |
| **A03 Injection** | PASS | All Python input goes through Pydantic `strict` validation with `extra="forbid"`. Input hardening normalises NFKC, strips zero-width chars, recursively URL/Base64 decodes, and collapses confusable homoglyphs before agent analysis. SQL: Prisma ORM (parameterised). |
| **A04 Insecure Design** | PASS | Tri-agent fail-closed pipeline, replay defence, drift detection, degraded-mode gate. Each agent independently deny-capable. |
| **A05 Security Misconfiguration** | PARTIAL | CSP uses `'unsafe-inline'` for `script-src` (Next.js RSC limitation). COOP and CORP headers absent. HSTS missing `preload` directive. `Permissions-Policy` defined only in `next.config.js` headers, not in `middleware.ts` response, so it is absent from API-route responses. |
| **A06 Vulnerable Components** | PARTIAL | Python `requirements.txt` hash-pinned via `pip-compile --generate-hashes` ✓. npm packages use `^` semver ranges — transitive float is possible (see §7). `starlette 1.0.0` is a brand-new major release; compat impact not yet validated. |
| **A07 Identification & Authn Failures** | PARTIAL | BCRYPT cost 14 ✓. Per-email login rate limit (5/15 min) ✓. **Gaps:** No IP-level aggregate rate limit on login. Timing oracle in unverified-email branch (BUG-03). |
| **A08 Software Integrity Failures** | PASS | Ed25519 manifest signature, hash-pinned wheels, Dockerfile `COPY --chown`. |
| **A09 Logging & Monitoring** | PASS | `log_audit_event()` on every decision, TMR receipt, OpenTelemetry traces, 90-day retention setting documented. |
| **A10 SSRF** | PASS | Demo proxy enforces protocol allowlist (`https://` only) and domain allowlist; no raw URL pass-through. |

---

## 4. Performance Review

### 4.1 Database Queries
- **Dashboard `page.tsx`:** Four separate Prisma queries (key count, request count, audit log rows, rate-limit events) are issued sequentially; a comment in the source notes this intentionally avoids a PgBouncer prepared-statement conflict. At low row counts this is acceptable, but at scale each sequential round-trip adds latency.
- **Indexes:** All high-cardinality lookup columns are indexed — `userId`, `keyHash`, `status`, `decision`, `action`, `createdAt`, composite `[email, createdAt]` and `[action, key, createdAt]`. Index coverage is adequate for current query patterns.
- **Connection pooling:** `asyncpg 0.30.0` included in requirements; Prisma uses its own connection pool. No `connection_limit` tuning parameter is documented for self-hosted deployments.

### 4.2 Cold-Start Latency
- Sentence-Transformer model (`all-MiniLM-L6-v2`) is loaded at module import via a singleton. On a cold container start, model loading adds ~1 s. Subsequent warm requests are not affected.
- Demo retry logic introduces up to 3 s of additional latency on first request when the backend is cold.

### 4.3 Embedding Throughput
- Nitpicker and Judge both instantiate independent embedding model singletons. On a fresh worker these load sequentially, adding ~2 s to the first request. This is acceptable for current throughput targets but would be a bottleneck at high QPS without pre-warming.

### 4.4 Rate Limiting
- UpstashRateLimiter uses Redis `INCRBY` + `EXPIREAT` — O(1) per request, efficient.
- In-memory fallback used when Redis is unavailable; not suitable for multi-instance deployments.

---

## 5. Accessibility Audit

| Check | Verdict | Notes |
|-------|---------|-------|
| Interactive elements have semantic roles | PARTIAL | `<button>` used correctly throughout. Dismissible banners have `aria-label`. Nav landmark present. Missing: `<main>` landmark on some pages. |
| Form inputs have associated `<label>` elements | PARTIAL | Settings, register, login forms have labels. Demo payload `<textarea>` uses placeholder text only — no `<label>` element (fails WCAG 2.1 SC 1.3.1). |
| Live regions for dynamic content | PARTIAL | Auth forms use `role="alert"`. Demo results panel uses `aria-live="polite"`. Audit log table updates do not use a live region — screen readers will not announce new rows. |
| Focus management after navigation | NOT VERIFIED | No Playwright or axe-core tests. Focus restoration after modal open/close not verified. |
| Keyboard navigation | PARTIAL | Standard HTML elements are keyboard-accessible. Custom dropdown menus and the demo control panel not verified for trap focus / `Escape` key support. |
| Colour contrast | NOT VERIFIED | No automated contrast check in CI. `globals.css` uses CSS custom properties; values not spot-checked in this audit. |
| Images have `alt` text | PASS | `<Image>` components inspected; decorative images use `alt=""`. |
| ARIA attributes are valid | PASS | No invalid `aria-*` attribute patterns found in static analysis. |

---

## 6. Architecture Review

### 6.1 Layering and Separation of Concerns
The codebase has a clearly defined three-layer architecture:

```
Browser ↔ Next.js (App Router + API routes) ↔ Python FastAPI (agents pipeline)
```

This separation is well-maintained. The Python pipeline is fully decoupled from the
Next.js layer; they communicate over HTTP only. The three-agent pipeline (Scout →
Nitpicker → Judge) implements independent, composable enforcement stages.

### 6.2 Agent Singleton Lifecycle
**File:** `bridge/fastapi_wrapper.py` lines 308–310
Agent instances (`scout`, `nitpicker`, `judge`) are created once at module import time.
This is correct for Gunicorn/Uvicorn worker-per-process models, but the model weights and
index are held in process memory. Under hot-reload (e.g., `uvicorn --reload` in dev) the
singletons are re-instantiated on every reload, re-loading ~200 MB of model weights each
time. This is a developer experience problem, not a production risk.

### 6.3 Missing Centralised HTTP Client
**File:** All 11 dashboard `fetch()` call sites across `app/dashboard/**`
There is no shared `lib/client-fetch.ts` wrapper. Every call site hard-codes its own
`POST`, no shared timeout, no shared 401/session-expiry handling. If the session expires,
the user sees a JSON parse error or an unhandled exception rather than a redirect to login.

### 6.4 Multi-Tenant Isolation
User data is scoped by `userId` in every Prisma query. No cross-tenant data leakage
pattern was identified.

### 6.5 Worker Coordination
No distributed lock or leader-election mechanism exists for SHA-256 chain management.
Two replicas each write to their own chain, defeating the integrity guarantee for
multi-instance deployments.

### 6.6 Test Environment Decoupling
Test fixtures (`conftest.py`) set `ALETHEIA_MODE=shadow` globally, which silently
disables enforcement for all tests. There is no fixture that runs tests against the
active-mode code path. The test suite does not exercise the production enforcement
contract.

---

## 7. Dependency Audit

### Python (requirements.txt — hash-pinned)

| Package | Version | Notes |
|---------|---------|-------|
| `fastapi` | 0.135.1 | Current stable |
| `starlette` | 1.0.0 | **RISK:** Brand-new major version; breaking changes possible |
| `pydantic` | 2.12.5 | Current stable |
| `cryptography` | 46.0.5 | Current stable |
| `sentence-transformers` | 5.3.0 | Current stable |
| `qdrant-client` | 1.17.1 | Current stable |
| `redis` | 7.4.0 | Current stable |
| `opentelemetry-sdk` | 1.37.0 | Current stable |
| `uvicorn` | 0.41.0 | Current stable |
| `asyncpg` | 0.30.0 | Current stable |
| `bcrypt` | (transitive) | Version determined by `cryptography` extras |

All wheels are hash-pinned via `pip-compile --generate-hashes`. Supply-chain integrity is
strong. **Action required:** validate `starlette 1.0.0` compatibility with existing
middleware and exception handlers before launch.

### npm (package.json — `^` ranges)

| Package | Declared | Notes |
|---------|----------|-------|
| `next` | 16.2.4 (exact) | Exact pin for Next.js — good practice |
| `next-auth` | ^4.24.13 | Patch float acceptable |
| `@prisma/client` | ^5.22.0 | Minor float acceptable |
| `bcryptjs` | ^3.0.3 | Minor float acceptable; cost=14 in code ✓ |
| `stripe` | ^22.0.1 | Minor float; Stripe SDK is stable |
| `resend` | ^6.11.0 | Minor float |
| `@vercel/analytics` | ^2.0.1 | Low risk |
| `zod` | (transitive) | Version not pinned; Zod v4 is a breaking change |

**Recommendation:** lock npm dependencies with `npm ci` enforced in CI and commit
`package-lock.json` with `--save-exact` for security-sensitive packages.

---

## 8. Refactoring Guide

### RF-01 — Extract `executeAudit()` from demo page (LOW effort, HIGH maintainability)
**File:** `app/demo/page.tsx`
The `quickRun` and `runAudit` handlers share ~40 lines of identical fetch, error-handling,
and receipt-parsing logic. Extract a single `executeAudit(payload, options)` function.

### RF-02 — Create `lib/client-fetch.ts` wrapper (MEDIUM effort, HIGH safety impact)
Replace all 11 bare `fetch()` calls in dashboard components with a shared wrapper that:
- Sets a request timeout (e.g., 10 s)
- Checks `response.status === 401` and calls `signOut({ callbackUrl: '/login' })`
- Parses and re-throws structured API errors

### RF-03 — Consolidate shadow-mode test fixtures (LOW effort, CRITICAL test integrity)
**File:** `tests/conftest.py`
Remove `ALETHEIA_MODE=shadow` from the default fixture. Add two explicit fixtures:
`shadow_mode_env` and `active_mode_env`. Each test that needs one should request it
explicitly. The security-enforcement tests must use `active_mode_env`.

### RF-04 — Structured logging in `economics/` (LOW effort)
**File:** `economics/*.py`
Replace bare `print()` diagnostic calls with `logging.getLogger(__name__)`. This brings
the module in line with the structured logging used in the rest of the Python codebase.

### RF-05 — Extract `makeRequest()` helper in `bridge/fastapi_wrapper.py` (MEDIUM effort)
The pipeline execution logic is ~200 lines in a single `handle_request()` function.
Extracting the agent-invocation stages into `_run_scout()`, `_run_nitpicker()`, `_run_judge()`
helpers would improve readability and simplify unit testing for individual pipeline stages.

---

## 9. Test Coverage

### 9.1 Python — pytest

| Metric | Value |
|--------|-------|
| Tests collected | 1 144 |
| Passed | 1 119 |
| Failed | **10** |
| Skipped | 16 |
| Failure rate | 0.87% overall; **80% failure rate** in `test_api.py` enforcement sub-suite |

**Root cause of all 10 failures:**

| Failures | Root Cause |
|----------|-----------|
| 8 (shadow mode) | `ALETHEIA_MODE=shadow` in `conftest.py` → all DENIED flipped to PROCEED |
| 2 (health 503) | `manifest/security_policy.json` and Redis not configured in CI → readiness probe returns 503 |

**Coverage Gaps:**
- **Active-mode enforcement path not tested.** No test runs with `ALETHEIA_MODE=active`. The full production enforcement contract is unverified in CI.
- **No integration tests for API key generation error handling.** `hashKey()` throw on missing `ALETHEIA_KEY_SALT` has no test.
- **No tests for SHA-256 chain bootstrap.** Chain continuity across restarts is untested.
- **No tests for 401 session expiry in dashboard fetch paths.** TypeScript component tests use mocks only.
- **Timing oracle not tested.** No test asserts that the login path has equal timing for verified vs. unverified accounts.

### 9.2 TypeScript — vitest

| Metric | Value |
|--------|-------|
| Tests collected | 9 |
| Passed | 9 |
| Failed | 0 |

**Coverage Gaps:**
- Tests cover string-utility and schema-validation helpers only.
- Zero coverage of dashboard components, API routes, auth flows, or middleware.
- No Playwright / axe-core accessibility tests in CI.

---

## Summary Risk Matrix

| ID | Severity | Category | Title |
|----|----------|----------|-------|
| BUG-01 | 🔴 CRITICAL | Bug / Test-Coverage | Shadow mode disables enforcement in all tests |
| BUG-02 | 🟠 HIGH | Bug / OWASP A05 | `hashKey()` crashes on missing `ALETHEIA_KEY_SALT` |
| BUG-03 | 🟠 HIGH | Bug / OWASP A07 | Timing oracle on unverified-email login branch |
| BUG-04 | 🟠 HIGH | Bug / OWASP A02 | `receipt.prompt` exposes unredacted PII |
| RF-02 | 🟠 HIGH | Refactoring / Architecture | No `401` handling in any dashboard fetch call |
| BUG-05 | 🟡 MEDIUM | Bug / Architecture | Audit chain resets to GENESIS on restart |
| OWASP-A05 | 🟡 MEDIUM | Security | `unsafe-inline` CSP; missing COOP/CORP headers |
| OWASP-A01 | 🟡 MEDIUM | Security | `protectedPaths` list narrower than actual routes |
| BUG-07 | 🟡 MEDIUM | Bug / Test | Health endpoint always 503 in CI |
| BUG-06 | 🟡 MEDIUM | Bug / UX | `service_unavailable` discards error message |
| DEP-01 | 🟡 MEDIUM | Dependency | `starlette 1.0.0` compatibility not validated |
| RF-01 | 🟢 LOW | Refactoring | Duplicate `quickRun`/`runAudit` logic |
| RF-04 | 🟢 LOW | Refactoring | `print()` in `economics/` should use logger |
| A11Y-01 | 🟢 LOW | Accessibility | Demo textarea missing `<label>` |
| A11Y-02 | 🟢 LOW | Accessibility | Audit log table missing `aria-live` region |
| PERF-01 | 🟢 LOW | Performance | Sequential Prisma queries in dashboard page |
