# Aletheia Core - Implementation-First Checklist

Date: 2026-04-30
Source packet: docs/audit-findings/UNIFIED_AUDIT_IMPLEMENTATION_PACKET_2026-04-30.md

Purpose: execution-only guide. This strips narrative and keeps only what to change, in what order, and how to verify.

---

## 0) Launch Gate

Current state: CONDITIONAL NO-GO.

You should treat these four as hard blockers before launch:
1. P1-1 Shadow-mode test contamination
2. P1-3 Receipt prompt PII leak
3. P1-2 Key-generation crash when salt missing
4. P1-4 Login timing oracle for unverified email

Definition of GO for this checklist:
- All Phase 1 items completed and merged
- Focused suites pass in active mode
- Launch readiness checklist items 1-4 and 14 moved to met

---

## 1) Immediate Work Queue (Phase 1)

### P1-1 - Fix shadow-mode test contamination (CRITICAL)

Files:
- tests/conftest.py
- tests/test_api.py
- tests/test_redteam_adversarial.py
- tests/test_swarm_1000bot.py

Changes:
1. Remove global default ALETHEIA_MODE=shadow from common fixture.
2. Add explicit fixtures:
   - active_mode_env -> sets ALETHEIA_MODE=active
   - shadow_mode_env -> sets ALETHEIA_MODE=shadow
3. Apply active_mode_env to tests that assert DENIED behavior.
4. Keep only explicit shadow-behavior tests on shadow_mode_env.

Verification commands:
- pytest tests/test_api.py tests/test_redteam_adversarial.py tests/test_swarm_1000bot.py -q
- pytest tests/test_api.py::TestAPI::test_shadow_mode_overrides_deny_to_proceed -q

Exit criteria:
- Enforcement tests validate active behavior, not shadow behavior.
- Shadow-mode behavior remains tested explicitly.

---

### P1-2 - Guard API key hashing when ALETHEIA_KEY_SALT is missing (HIGH)

Files:
- app/api/keys/route.ts
- docs/ENVIRONMENT_VARIABLES.md

Changes:
1. Add early env guard in POST handler.
2. Return structured JSON error, do not throw uncaught exception.
3. Mark ALETHEIA_KEY_SALT as required in environment docs.

Verification commands:
- pnpm test (or npm test if repo uses npm scripts)
- Add or run route test covering missing ALETHEIA_KEY_SALT

Exit criteria:
- Missing salt returns controlled error response.
- No generic 500 crash page from uncaught throw.

---

### P1-3 - Redact receipt.prompt PII (HIGH)

Files:
- core/audit.py
- tests/test_pii_redaction.py (or nearest receipt tests)

Changes:
1. Change build_tmr_receipt(prompt=payload) to build_tmr_receipt(prompt=redact_pii(payload)).
2. Add test with payload containing email/phone/SSN and assert receipt.prompt is redacted.

Verification commands:
- pytest tests/test_pii_redaction.py -q
- pytest tests/test_enterprise.py -q

Exit criteria:
- No raw PII survives in receipt.prompt.
- Receipt signature verification still passes.

---

### P1-4 - Close unverified-email login timing oracle (HIGH)

Files:
- lib/auth.ts
- auth tests in tests-ts or related auth test files

Changes:
1. In !user.emailVerified branch, execute bcrypt.compare against stored hash before return.
2. Call recordLoginFailure(email) in that branch.
3. Keep returned user message generic.

Verification commands:
- Run auth unit/integration tests
- Add test asserting recordLoginFailure called for unverified branch

Exit criteria:
- Both wrong-password and unverified-email flows consume comparable work and failure accounting.

---

### P1-5 - Make health tests deterministic in CI (MEDIUM)

Files:
- bridge/fastapi_wrapper.py
- tests/conftest.py
- tests/test_api.py (health tests)

Changes (choose one approach):
1. Add test-only bypass flag for manifest/redis checks in readiness path, or
2. Mock manifest and redis in dedicated unit health tests.

Verification commands:
- pytest tests/test_api.py::TestHealthReadinessEndpoints -q

Exit criteria:
- Health tests do not fail because infra is absent in CI.

---

## 2) Recommended Implementation Order (Today)

1. P1-1 first (restores trust in security test signal)
2. P1-3 second (data leak blocker)
3. P1-2 third (availability blocker)
4. P1-4 fourth (auth hardening blocker)
5. P1-5 fifth (CI stability)

Reason: this order maximizes signal quality early and eliminates launch blockers fastest.

---

## 3) Validation Matrix After Phase 1

Run in this order:
1. pytest tests/test_api.py tests/test_redteam_adversarial.py tests/test_swarm_1000bot.py -q
2. pytest tests/test_pii_redaction.py tests/test_enterprise.py -q
3. pytest tests/test_judge_manifest.py tests/test_audit_extended.py tests/test_unified_audit.py -q
4. Full Python suite: pytest tests/ -q
5. TypeScript tests: run project test script for tests-ts

Expected outcome:
- Security enforcement assertions pass in active mode.
- Receipt redaction tests pass.
- No regressions in manifest/audit/signing suites.

---

## 4) Next Sprint (Phase 2) - Queue Only

Plan these immediately after Phase 1 merge:
- P2-1 Add IP-level login rate limit
- P2-6 Centralized client fetch with 401 handling
- P2-4 Add COOP/CORP headers
- P2-5 Ensure Permissions-Policy in middleware response path
- P2-2 Audit chain continuity across restart
- P2-3 CSP nonce migration off unsafe-inline
- P2-7 HSTS preload

---

## 5) Done Definition for Launch

All must be true:
- Blockers P1-1 through P1-4 complete
- Focused enforcement suites pass
- docs/ENVIRONMENT_VARIABLES.md updated for ALETHEIA_KEY_SALT required status
- Receipt PII test green and linked in CI
- Launch readiness checklist updated to GO status

---

## 6) Optional Tracking Board Template

Use this in your issue tracker:
- [ ] P1-1 Shadow-mode fixtures split
- [ ] P1-2 Key salt guard + docs
- [ ] P1-3 Receipt prompt redaction + tests
- [ ] P1-4 Unverified login timing fix + tests
- [ ] P1-5 Health CI determinism
- [ ] Phase 1 validation matrix complete
- [ ] Launch checklist updated
