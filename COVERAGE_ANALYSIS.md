# Test Coverage Analysis — Aletheia Core

> Generated: 2026-05-24  
> Branch: `claude/test-coverage-analysis-PC2OB`  
> Test run: `pytest tests/ --cov=core --cov=guards --cov=detectors --cov=crypto --cov=server --cov=manifest --cov=bridge -m "not integration"`  
> **Overall result: 1,317 passed · 67 skipped · 75% line coverage (6,448 lines measured)**

---

## Executive Summary

The Python test suite is large (73 test files, 1,300+ passing tests) and covers most of
the hot paths well. However, several high-security modules are either completely untested
or have dangerously low coverage. The TypeScript side has only 17 test files covering a
fraction of the Next.js frontend.

| Tier | Modules | Covered | Priority |
|------|---------|---------|----------|
| **0 % — completely dark** | `core/auth/oidc.py`, `core/auth/saml.py`, `core/persistence/pg_decision_store.py`, `core/persistence/pg_key_store.py`, `bridge/fastapi_wrapper.py` | 0 / ~390 lines | 🔴 Critical |
| **< 35 % — severely undertested** | `core/auth/hosted_prisma_bridge.py` (24%), `core/canonicalization.py` (26%), `core/secrets/{aws,gcp,vault,azure}.py` (~30–34%) | ~30 / 290 lines | 🔴 Critical |
| **35–60 % — undertested** | `core/db.py` (39%), `core/model_loader.py` (46%), `core/redis_pool.py` (49%), `guards/distributed_state.py` (55%), `core/manifest_cache.py` (55%), `server/websocket.py` (60%), `core/runtime_bootstrap.py` (60%) | ~140 / 320 lines | 🟡 High |
| **60–80 % — partial coverage** | `server/app.py` (63%), `core/ws_audit.py` (69%), `core/rate_limit.py` (69%), `server/middleware.py` (76%), `server/_bridge.py` (73%), `crypto/tpm_interface.py` (78%) | ~200 / 690 lines | 🟡 High |
| **TypeScript (no coverage tool)** | 14+ React components, 17+ API routes, all landing/SEO pages | — | 🟠 Medium |

---

## 🔴 Priority 1 — 0 % Coverage (Completely Untested)

### 1. `core/auth/oidc.py` — 0 % (156 lines)

**Why it matters:** OIDC is the primary enterprise SSO path. A bug here silently admits
unauthenticated users or rejects valid sessions. Every security property of the IdP
integration (signature verification, expiry, audience/issuer binding, role mapping) is
completely untested.

**What to test:**

| Test case | What it proves |
|-----------|---------------|
| `OIDCAuthProvider.__init__` raises `ImportError` when `authlib` absent | Dependency guard works |
| `__init__` raises `ValueError` with empty issuer | Config validation |
| `authenticate("")` returns `None` | Empty credential short-circuit |
| `authenticate("Bearer <valid_jwt>")` with mocked JWKS → valid `AuthenticatedUser` | Happy path |
| JWT with wrong `iss` → `None` | Issuer mismatch rejection |
| JWT with wrong `aud` (string) → `None` | Audience mismatch (scalar) |
| JWT with wrong `aud` (list) → `None` | Audience mismatch (list) |
| Expired JWT → `None` | Token expiry |
| JWKS fetch timeout (httpx `ConnectError`) → `None` | Network failure graceful degradation |
| JWKS cache: second call within TTL does not re-fetch | Cache hit |
| Unknown role claim → defaults to `"operator"` | Role fallback |
| `tenant_id` and `aletheia_tenant` claims both extracted | Tenant mapping |
| `Bearer ` prefix stripped before validation | Prefix stripping |
| `health_check()` returns `True` when IdP responds 200 | Health probe |
| `health_check()` returns `False` on network error | Health probe failure |

**Suggested test file:** `tests/test_oidc_auth.py`  
**Mocking strategy:** `unittest.mock.patch` on `httpx.AsyncClient.get` to return fake
JWKS and discovery JSON; use `authlib.jose` directly to sign test tokens with a local
RSA or EC key pair, or mock `_jwt.decode` + `claims.validate`.

---

### 2. `core/auth/saml.py` — 0 % (154 lines)

**Why it matters:** SAML is the other enterprise SSO path. The module does strict
XML signature validation — if the test suite never exercises this, regressions in
attribute mapping or signature-check bypasses go undetected.

**What to test:**

| Test case | What it proves |
|-----------|---------------|
| `SAMLAuthProvider.__init__` raises `ImportError` when `python3-saml` absent | Dependency guard |
| `__init__` raises `ValueError` with missing `metadata_url` | Config validation |
| Valid SAML response → `AuthenticatedUser` with correct `email`, `role`, `tenant_id` | Happy path |
| Attribute fallback: `mail` → `email`, `cn` → `displayName` | Attribute aliases |
| Missing `aletheia_role` falls back to `role`, then defaults to `"operator"` | Role fallback chain |
| Missing `aletheia_tenant` falls back to `tenant_id` | Tenant fallback |
| Invalid/malformed SAML response → `None` (no exception raised) | Error encapsulation |
| SAML error response (non-authenticated) → `None` | Auth failure path |

**Suggested test file:** `tests/test_saml_auth.py`  
**Mocking strategy:** Mock the `onelogin.saml2` SDK's `Auth` class to control response attributes.

---

### 3. `core/persistence/pg_decision_store.py` — 0 % (64 lines)

**Why it matters:** This is the production decision store used for replay-token claiming
under real load. Zero test coverage means schema migrations, multi-tenant isolation, and
concurrency semantics are entirely untested.

**What to test:**

| Test case | What it proves |
|-----------|---------------|
| `init_db()` creates schema version table and token table | Schema initialization |
| `claim_token(token, tenant_id)` returns `True` on first call | Happy path |
| Duplicate `claim_token` returns `False` (replay protection) | Idempotency |
| `claim_token` for different tenants with same token → both succeed | Tenant isolation |
| `purge_expired()` removes tokens past TTL | TTL enforcement |
| Pool unavailable → `degraded` flag set | Graceful degradation |

**Suggested test file:** `tests/test_pg_decision_store.py`  
**Mocking strategy:** Use `asyncpg` with `asynctest` mock or `asyncpg.testing` pool,
or mock the pool's `acquire()` context manager via `AsyncMock`.

---

### 4. `core/persistence/pg_key_store.py` — 0 % (102 lines)

**Why it matters:** PostgreSQL key store is the production backend for API key management.
Zero coverage leaves CRUD operations, quota enforcement, and tenant scoping entirely untested.

**What to test:** CRUD lifecycle (create/lookup/delete), quota check enforcement, tenant-scoped
lookups, and pool unavailability degradation.

**Suggested test file:** `tests/test_pg_key_store.py`  
**Mocking strategy:** Same as `pg_decision_store` — mock `asyncpg` pool via `AsyncMock`.

---

### 5. `bridge/fastapi_wrapper.py` — 0 % (unmeasured lines)

**Why it matters:** The bridge layer is the integration point between the Python backend
and external consumers. Untested means request routing, error wrapping, and health-check
pass-through are all dark.

---

## 🔴 Priority 2 — < 35 % Coverage

### 6. `core/canonicalization.py` — 26 % (178 / 240 lines uncovered)

**Why it matters:** This is the **security-critical input canonicalization pipeline** that
sanitizes every untrusted input before audit decisions. It defends against Unicode attacks,
zero-width injection, bidirectional overrides, confusable-character spoofing, multi-layer
URL/Base64/HTML encoding, and data URI injection. At 26% coverage, virtually the entire
multi-layer decode engine is untested — the exact code that adversaries will target.

**Uncovered sections (lines 118–290, 305–357, 364–405):**
- `canonicalize()` for oversized input (quarantine path)
- All 6 decode layers: URL, Base64, HTML entity, Unicode escape, hex, data URI
- `_looks_like_base64()` with various inputs
- `_decode_unicode_escapes()` with `\uXXXX` / `\xXX` sequences
- `_try_hex_decode()` with valid and invalid hex strings
- `_strip_data_uris()` inline base64 replacement
- `_calculate_entropy()` for high- and low-entropy strings
- `canonicalize_untrusted_text()` public API with custom policy

**What to test (representative sample):**

| Test case | Attack vector covered |
|-----------|----------------------|
| URL-encoded injection: `%69%67%6e%6f%72%65` | URL encoding evasion |
| Double URL-encoded: `%2569%256e%256a%2565%2563%2574` | Double-encode evasion |
| Base64-encoded payload: `aWdub3Jl` | Base64 obfuscation |
| HTML entity injection: `&#105;&#103;&#110;&#111;&#114;&#101;` | HTML entity evasion |
| Unicode escape: `ignore` | Unicode escape evasion |
| Hex-encoded: `69676e6f7265` | Hex encoding evasion |
| Data URI: `data:text/plain;base64,aWdub3Jl` | Data URI injection |
| Mixed layers: base64(URL(html_entity(payload))) | Layered encoding |
| Text > 50,000 chars → quarantined | Size guard |
| High-entropy string (random bytes) → `entropy_flag=True` | Entropy detection |
| Zero-width chars stripped | ZW injection |
| BiDi override chars stripped | BiDi attack |
| Cyrillic confusables collapsed to Latin | Confusable spoofing |
| Custom policy: `max_entropy=100` → no flag | Policy override |
| Budget exhaustion: many decode steps → `decode_budget_exhausted=True` | Budget guard |

**Suggested test file:** `tests/test_canonicalization_extended.py`

---

### 7. `core/secrets/{aws,gcp,azure,vault}.py` — 30–34 % each

**Why it matters:** These are the production secret backends. Low coverage means
authentication flows, connection failures, retry logic, and secret parsing are all dark
in production-critical paths.

**What to test for each backend:**
- Successful secret fetch with mocked SDK client
- SDK client missing (`ImportError`) raises `RuntimeError` or returns `None` gracefully
- Network/API error → exception propagated or gracefully handled
- Secret not found (e.g., AWS `ResourceNotFoundException`) → `None`
- Secret version selection (AWS) and secret path formation

**Suggested test files:** `tests/test_secrets_backends.py`  
**Mocking strategy:** `unittest.mock.patch` on cloud SDK clients
(`boto3.client`, `azure.keyvault.secrets.SecretClient`, etc.).

---

### 8. `core/auth/hosted_prisma_bridge.py` — 24 %

**What to test:**
- `hash_hosted_api_key()` with and without key salt
- `normalize_utc()` with naive and tz-aware datetimes
- `current_utc_month_bounds()` across December/January boundary
- `check_hosted_prisma_api_key()` with valid/invalid/expired keys via mocked pool

---

## 🟡 Priority 3 — 35–70 % Coverage

### 9. `core/ws_audit.py` — 69 % (40 / 131 lines uncovered)

**Uncovered paths (lines 121–163, 212–213, 226, 235–236):**
- `ws_audit_handler()`: the full WebSocket lifecycle (accept, subscribe, message loop, heartbeat, disconnect)
- `create_ws_token()` public API
- `_verify_ws_jwt()` with valid, expired, tampered, and malformed tokens
- `_authenticate_ws_token()`: admin key path, key_store lookup path, fallback `None`
- `AuditBroadcast.publish()` with `__all__` tenant (admin subscription)
- `publish()` with full queue → stale connection removal

**What to test:**

| Test case | What it proves |
|-----------|---------------|
| `AuditBroadcast.subscribe()` increments `WS_CONNECTIONS` | Metrics correctness |
| `publish()` delivers to matching tenant | Tenant-scoped fan-out |
| `publish()` with `__all__` subscriber receives all tenants | Admin subscription |
| `publish()` to full queue → stale connection removed | Back-pressure handling |
| `create_ws_token()` + `_verify_ws_jwt()` round-trip | JWT create/verify |
| `_verify_ws_jwt()` with expired token → `None` | Expiry enforcement |
| `_verify_ws_jwt()` with tampered signature → `None` | Signature integrity |
| `_verify_ws_jwt()` without `ALETHEIA_WS_JWT_SECRET` → `None` | Disabled path |
| `_authenticate_ws_token()` with admin key → `"__all__"` | Admin auth |
| `ws_audit_handler()` with missing token → close(4001) | Missing token |
| `ws_audit_handler()` with invalid token → close(4003) | Invalid token |
| `ws_audit_handler()` over connection limit → close(4029) | Rate limit |
| Heartbeat ping sent after timeout | Keepalive |

**Suggested test file:** `tests/test_ws_audit_extended.py`  
**Mocking strategy:** Use `starlette.testclient.TestClient` with WebSocket support,
or mock `WebSocket` directly with `AsyncMock`.

---

### 10. `guards/distributed_state.py` — 55 % (30 / 67 lines uncovered)

**Uncovered paths (lines 159–238):** All three manager methods —
`get_breaker`, `set_breaker`, `atomic_transition_breaker`, `get_velocity`,
`increment_velocity`, `update_swarm_bucket`.

**What to test:**
- `get_breaker()` with and without existing state in Redis
- `atomic_transition_breaker()` Lua script: OPEN→HALF_OPEN valid transition
- `atomic_transition_breaker()` blocks illegal OPEN→CLOSED transition
- `atomic_transition_breaker()` respects active cooldown
- `increment_velocity()` sliding window resets on boundary
- `update_swarm_bucket()` exponential moving average computation

**Suggested test file:** `tests/test_distributed_state_extended.py`  
**Mocking strategy:** Use `fakeredis` (`pip install fakeredis`) for a full in-process
Redis implementation that supports Lua scripts.

---

### 11. `core/rate_limit.py` — 69 % (72 / 230 lines uncovered)

**Uncovered paths (lines 90–109, 188–214, 297–306, 397–486):**
- Redis circuit breaker: open state, probe slot, reset after recovery
- Upstash error parsing for malformed responses
- `eval_rate_limiter` burst window
- Per-minute + per-burst combined enforcement

**What to test:**
- Circuit opens after 5 consecutive Redis failures
- Probe slot allows ~10% of requests through during outage
- Circuit closes on probe success
- `eval_rate_limiter`: combined per-minute + burst enforcement
- In-memory fallback LRU eviction at 50k IP cap

---

### 12. `server/middleware.py` — 76 % (12 / 50 lines uncovered)

**Uncovered paths (lines 63, 97–98, 122–136):**
- `internal_secret_guard`: path `/v1/*` with missing or wrong `x-aletheia-internal` header → 403
- Security header values (CSP, X-Frame-Options, etc.)
- Rate-limit header injection when `remaining` / `retry_after` present

**What to test:**
- `/v1/anything` with correct internal secret → passes through
- `/v1/anything` with wrong secret → 403
- `/health` bypasses internal secret check
- Response contains `X-Frame-Options: DENY`
- Response contains `X-Content-Type-Options: nosniff`
- Rate-limit headers present when limiter returns remaining count

---

### 13. `server/app.py` — 63 % (57 / 155 lines uncovered)

**Uncovered paths (lines 88–232):**
- `lifespan()` startup/shutdown: DB pool creation, Qdrant ping, model loading, shutdown cleanup
- Multiple startup branches: with/without `ALETHEIA_DATABASE_URL`
- `lifespan()` error handling when dependencies fail

**What to test:**
- App startup with all env vars → `app.state` populated correctly
- Startup without optional deps (Qdrant, Postgres) → degraded mode, no crash
- Shutdown properly closes pool and Qdrant client

---

## 🟠 Priority 4 — TypeScript / Frontend

The 17 TypeScript test files cover roughly 20% of the frontend surface. The biggest
untested areas:

### 14. React Component Unit Tests (0 tested)

No React components have unit tests. The highest-value components to test:

| Component | Why |
|-----------|-----|
| `components/ErrorBoundary.tsx` | Prevents white-screen crashes for all users |
| `components/Nav.tsx` | Auth-state-dependent rendering (logged in vs. out) |
| `components/dashboard/DashboardSidebar.tsx` | Navigation, active route highlighting |
| `components/onboarding/OnboardingWizard.tsx` | Complex multi-step stateful flow |
| `components/ROICalculator.tsx` | User-facing calculation logic |

**Tool:** Vitest + `@testing-library/react`

### 15. Untested API Routes

| Route | Risk |
|-------|------|
| `api/account/export/route.ts` | Data export — must be auth-gated and tenant-scoped |
| `api/evidence/route.ts` | Evidence submission — must validate input |
| `api/settings/route.ts` | Account settings mutation |
| `api/stripe/webhook/route.ts` | Payment events — signature verification already tested but event handling is not |
| `api/auth/verify-email/route.ts` | Email verification link — one-time token consumption |

### 16. Authentication Flow E2E Tests

No test exercises the full login → session → dashboard → logout flow. This should be
covered with Playwright or Cypress E2E tests.

---

## Quick-Win Opportunities

These gaps have high ROI because the code is already well-structured and tests
can be written quickly with standard mocking:

1. **`core/auth/hosted_prisma_bridge.py`** — Pure functions (`hash_hosted_api_key`,
   `normalize_utc`, `current_utc_month_bounds`) need no mocks at all. ~15 lines of tests
   get from 24% → ~70%.

2. **`core/canonicalization.py`** — The `_looks_like_base64`, `_try_hex_decode`,
   `_calculate_entropy` helpers are pure functions. Parametrized tests with 20 inputs
   each jump coverage from 26% → ~65%.

3. **`core/model_loader.py`** — 46% uncovered but only 24 lines total. Two mock tests
   (model available / model missing) would bring it to ~90%.

4. **`manifest/signing.py`** — 90% already, but the 10% gap includes the error path on
   malformed manifests. One test for each error type closes the gap.

---

## Recommended Actions

```
Week 1 (Critical Security Gaps)
├── tests/test_oidc_auth.py           — OIDC provider, ~15 tests
├── tests/test_saml_auth.py           — SAML provider, ~8 tests
└── tests/test_canonicalization_extended.py — Decode pipeline, ~20 tests

Week 2 (Storage + Distribution)
├── tests/test_pg_decision_store.py   — asyncpg mock, ~6 tests
├── tests/test_pg_key_store.py        — asyncpg mock, ~6 tests
├── tests/test_distributed_state_extended.py — fakeredis, ~8 tests
└── tests/test_secrets_backends.py    — 4 cloud backends, ~16 tests

Week 3 (Server + WebSocket)
├── tests/test_ws_audit_extended.py   — WS handler + JWT, ~13 tests
├── tests/test_middleware_extended.py — internal-secret guard, headers, ~8 tests
└── tests/test_server_app.py          — lifespan startup/shutdown, ~6 tests

Week 4 (Frontend)
├── tests-ts/error-boundary.test.tsx  — React ErrorBoundary
├── tests-ts/nav.test.tsx             — Nav auth state rendering
├── tests-ts/account-export.test.ts   — Export API auth gate
└── tests-ts/email-verify.test.ts     — Email verification flow
```

Adding Week 1 alone would close ~390 completely dark lines and raise overall line coverage
from **75% → ~82%**. Completing all four weeks would bring coverage above **90%**.
