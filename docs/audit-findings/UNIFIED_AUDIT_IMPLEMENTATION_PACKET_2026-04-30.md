# Aletheia Core - Unified Audit and Implementation Packet

Generated: 2026-04-30

This document combines the following sources in order:

1. docs/AUDIT_FINDINGS_CRYPTO_BINDING_2026-04-30.md
2. docs/audit-findings/FINAL_AUDIT_REPORT_2026-04-30.md
3. docs/audit-findings/LAUNCH_READINESS_2026-04-30.md
4. docs/audit-findings/PHASED_FIX_PLAN_2026-04-30.md

---

## Source 1: AUDIT_FINDINGS_CRYPTO_BINDING_2026-04-30.md

# Audit Findings: Decision Pipeline Cryptographic Binding

Date: 2026-04-30
Scope: Aletheia-Core decision pipeline, receipt signing, and manifest/action fail-closed behavior.

## Findings

### 1. High: Not every decision path emits a signed receipt

- The evaluate endpoint explicitly returns decisions without writing a receipt:
  - bridge/fastapi_wrapper.py#L901
  - bridge/fastapi_wrapper.py#L909
  - bridge/fastapi_wrapper.py#L969
  - bridge/fastapi_wrapper.py#L978
- This violates the requirement if "every PROCEED or DENIED decision" includes both audit and evaluate decisions.

### 2. High: Receipt policy hash can drift from the actual policy used for decisioning

- Receipt policy hash is recomputed from manifest bytes at log time, without signature verification:
  - core/audit.py#L102
  - core/audit.py#L113
  - core/audit.py#L252
  - core/audit.py#L274
- Judge policy is loaded once from verified manifest at initialization:
  - agents/judge_v1.py#L202
  - agents/judge_v1.py#L213
- If manifest file changes after startup (and before reload), a receipt may bind to a different hash than the in-memory policy that made the decision.

### 3. Medium: Unsigned receipt mode still exists outside active mode

- Receipt builder returns UNSIGNED_DEV_MODE when secret is absent:
  - core/audit.py#L398
  - core/audit.py#L404
- Startup blocks missing secret only when mode is active:
  - bridge/fastapi_wrapper.py#L433
  - bridge/fastapi_wrapper.py#L442
- So "every decision is HMAC-SHA256 signed" is conditionally true, not universal across all runtime modes.

### 4. Medium: Invalid manifest handling is fail-closed, but not always a returned DENIED response

- Tampered manifest raises and propagates in Judge load:
  - agents/judge_v1.py#L205
  - agents/judge_v1.py#L219
- Judge is instantiated at module import:
  - bridge/fastapi_wrapper.py#L310
- Result is startup failure (service unavailable), which is fail-closed but not an API-level DENIED status.

## Verified Controls That Are Correct

- Receipt signature algorithm is HMAC-SHA256:
  - core/audit.py#L406
  - core/audit.py#L410
  - core/audit.py#L434
  - core/audit.py#L439
- Canonical binding includes decision, policy_hash, payload_sha256, action, and origin:
  - core/audit.py#L211
  - core/audit.py#L215
  - core/audit.py#L220
  - core/audit.py#L223
  - core/audit.py#L380
  - core/audit.py#L387
- Audit endpoint path logs and generates a receipt for normal pipeline decisions:
  - bridge/fastapi_wrapper.py#L1150
  - core/audit.py#L335
  - core/audit.py#L349
- Unverifiable action context fails closed in Judge (no policy loaded):
  - agents/judge_v1.py#L248
  - agents/judge_v1.py#L249
  - bridge/fastapi_wrapper.py#L1111
  - bridge/fastapi_wrapper.py#L1124
- Ed25519 manifest verification checks are comprehensive (algorithm, key id/version, version/expiry metadata, payload hash, signature length, signature verification):
  - manifest/signing.py#L205
  - manifest/signing.py#L209
  - manifest/signing.py#L213
  - manifest/signing.py#L216
  - manifest/signing.py#L219
  - manifest/signing.py#L251
  - manifest/signing.py#L259
  - manifest/signing.py#L262

## Runtime Validation Performed

- Targeted tests passed:
  1. tests/test_signing.py: 25 passed
  2. tests/test_judge_manifest.py + tests/test_audit_extended.py + tests/test_redteam_fixes.py + tests/test_unified_audit.py: 88 passed
- Direct tamper verification run:
  1. Base receipt verified true
  2. Changing policy_hash, payload_sha256, action, origin, or decision each made verification false

## Open Assumption

- This audit assumes the requirement applies to all decision-returning API surfaces, not only /v1/audit.
- If scope is strictly /v1/audit in active mode with secret configured, compliance is much closer, with the main remaining concern being policy-hash drift after startup.

---

## Addendum: Three-Agent Evaluation Stack Deep-Dive

Date: 2026-04-30
Scope: Scout threat context scoring, Nitpicker semantic similarity blocking, Judge pre-execution veto, decision gating, and score leakage controls.

### Findings

#### 1. Medium: "All three must pass" is true in normal mode, but has a non-production shadow-mode exception

- The main decision gate denies when ANY single agent denies:
  - bridge/fastapi_wrapper.py#L951
  - bridge/fastapi_wrapper.py#L952
  - bridge/fastapi_wrapper.py#L953
  - bridge/fastapi_wrapper.py#L954
  - bridge/fastapi_wrapper.py#L1111
  - bridge/fastapi_wrapper.py#L1112
  - bridge/fastapi_wrapper.py#L1113
  - bridge/fastapi_wrapper.py#L1114
- In shadow mode outside production, a blocked decision can be flipped to PROCEED:
  - bridge/fastapi_wrapper.py#L1137
  - bridge/fastapi_wrapper.py#L1147
- Verified by test:
  - tests/test_api.py#L225
  - tests/test_api.py#L238

#### 2. Low: Nitpicker semantic extension is intentionally fail-open when Qdrant is degraded

- Static cosine blocking remains the safety floor, but Qdrant lookup errors degrade open:
  - agents/nitpicker_v2.py#L215
  - agents/nitpicker_v2.py#L247
  - agents/nitpicker_v2.py#L262
  - agents/nitpicker_v2.py#L204

### Agent-by-Agent Audit

#### Scout (threat context scoring)

- Uses heuristic scoring for smuggling prefixes, exfiltration markers, contextual camouflage (neutral anchors + high-value targets), and probing patterns:
  - agents/scout_v2.py#L127
  - agents/scout_v2.py#L148
  - agents/scout_v2.py#L159
  - agents/scout_v2.py#L173
  - agents/scout_v2.py#L194

#### Nitpicker (semantic similarity against blocked patterns)

- Performs cosine similarity against blocked pattern bank, with optional symbolic narrowing + Qdrant match and thresholding:
  - agents/nitpicker_v2.py#L155
  - agents/nitpicker_v2.py#L162
  - agents/nitpicker_v2.py#L165
  - agents/nitpicker_v2.py#L221
  - agents/nitpicker_v2.py#L225

#### Judge (pre-execution block decisions)

- Enforces restricted action IDs and applies cosine similarity against semantic camouflage aliases, plus grey-zone keyword escalation:
  - agents/judge_v1.py#L224
  - agents/judge_v1.py#L251
  - agents/judge_v1.py#L265
  - agents/judge_v1.py#L272
  - agents/judge_v1.py#L290

### Raw Threat Score Exposure Audit

- Client responses use discretized threat bands and omit raw `threat_score`:
  - bridge/fastapi_wrapper.py#L685
  - bridge/fastapi_wrapper.py#L688
  - bridge/fastapi_wrapper.py#L971
  - bridge/fastapi_wrapper.py#L1170
- Internal denial reasons are sanitized to avoid leaking similarity percentages, matched phrases, and keyword counts:
  - bridge/fastapi_wrapper.py#L700
  - bridge/fastapi_wrapper.py#L705
  - bridge/fastapi_wrapper.py#L716

### Runtime Validation Performed

- Focused red-team leakage and gating tests executed:
  1. tests/test_redteam_adversarial.py (`discretise_threat`, `response_never_contains_raw_score`, `sanitise_reason`, `multi_agent`) -> 6 passed
  2. tests/test_api.py (`shadow_mode_overrides_deny_to_proceed`) -> 1 passed

### Conclusion

- The stack is implemented as independent veto gates (Scout OR Nitpicker OR Judge can deny), so all three must pass for PROCEED in standard operation.
- Non-production shadow mode is the explicit operational exception where a blocked result may be surfaced as PROCEED for observability/testing.

---

## Addendum: Input Hardening Layer Verification

Date: 2026-04-30
Scope: Validation of NFKC normalization, zero-width/control stripping, recursive URL/Base64 decoding, and pipeline ordering before agent evaluation.

### Findings

#### 1. Confirmed: NFKC and confusable collapse are active

- NFKC normalization is applied at the start of normalization:
  - core/runtime_security.py#L258
- Confusable collapse is applied after decode/unescape:
  - core/runtime_security.py#L272
  - core/text_normalization.py
- Verified by tests:
  - tests/test_runtime_security_layer.py
  - tests/test_bridge_utils_extended.py#L44
  - tests/test_redteam_adversarial.py#L175

#### 2. Confirmed: Zero-width and control characters are stripped

- Zero-width and bidi markers are removed:
  - core/runtime_security.py#L88
  - core/runtime_security.py#L90
- Unicode control-category characters are removed globally:
  - core/runtime_security.py#L91
- Verified by tests:
  - tests/test_runtime_security_layer.py#L22
  - tests/test_bridge_utils_extended.py#L68
  - tests/test_redteam_fixes.py#L29

#### 3. Confirmed: Recursive URL/Base64/Data-URI decoding is bounded and active

- Recursive URL decoding with recursion/decode-budget limits:
  - core/runtime_security.py#L94
- Strict Base64 detection and bounded recursive decode:
  - core/runtime_security.py#L118
  - core/runtime_security.py#L159
- Data URI inline Base64 decoding:
  - core/runtime_security.py#L140
- Verified by tests:
  - tests/test_runtime_security_layer.py#L31
  - tests/test_bridge_utils_extended.py#L135
  - tests/test_redteam_fixes.py#L91
  - tests/test_enterprise_hardening_phase3.py#L100

#### 4. Confirmed: Hardening runs before Scout and Nitpicker in API paths

- Input is normalized into `clean_input` before any agent calls:
  - bridge/fastapi_wrapper.py#L920
  - bridge/fastapi_wrapper.py#L947
  - bridge/fastapi_wrapper.py#L948
  - bridge/fastapi_wrapper.py#L1048
  - bridge/fastapi_wrapper.py#L1099
  - bridge/fastapi_wrapper.py#L1102
- Normalization facade wiring:
  - bridge/utils.py#L8
  - bridge/utils.py#L13
- CLI path also normalizes before Scout/Nitpicker:
  - main.py#L42
  - main.py#L45
  - main.py#L51

### Runtime Validation Performed

- Targeted normalization suites executed and passed:
  1. tests/test_runtime_security_layer.py
  2. tests/test_bridge_utils_extended.py
  3. tests/test_redteam_fixes.py
  4. tests/test_enterprise_hardening_phase3.py
     Result: 93 passed.
- API instrumentation checks confirmed Scout, Nitpicker, and Judge received normalized payloads in both `/v1/evaluate` and `/v1/audit` flows.

### Conclusion

- Input Hardening is functioning as designed for the requested controls.
- NFKC/zero-width/recursive decode transformations are applied globally before Scout or Nitpicker evaluate payloads, reducing obfuscation-based evasion risk at agent entry.

---

## Addendum: Audit Persistence (Enterprise / Hosted Pro Compliance)

Date: 2026-04-30
Scope: Verification of 30-day retention functionality, independent receipt validation path, ISO/IEC 42001 alignment evidence, and "every AI action" signed-receipt coverage.

### Findings

#### 1. High: 30-day hosted audit retention is declared, but enforcement is not evidenced in the hosted data path

- Plan metadata declares 30-day retention for PRO/MAX/ENTERPRISE:
  - lib/hosted-plans.ts#L31
  - lib/hosted-plans.ts#L40
  - lib/hosted-plans.ts#L49
- Public docs/UX claims include 30-day retention:
  - README.md#L376
- Hosted log read/export endpoints do not apply a retention cutoff and can return all rows for a user (subject only to pagination/cursor):
  - app/api/logs/route.ts#L35
  - app/api/logs/route.ts#L40
  - app/api/evidence/route.ts#L16
  - app/api/evidence/route.ts#L21
- Data export endpoint explicitly uses a 90-day window and labels retention as 90 days:
  - app/api/account/export/route.ts#L60
  - app/api/account/export/route.ts#L110
- Privacy page states 90-day audit-log retention, conflicting with 30-day plan marketing:
  - app/legal/privacy/page.tsx#L89
- Infrastructure logrotate is configured for 30 rotated files for file logs, but this is separate from hosted Postgres audit-row lifecycle:
  - deploy/logrotate.conf#L3

#### 2. High: Receipt Viewer is not independent cryptographic verification

- Viewer page is an inspection/parser UI and explicitly defers full HMAC validation to a CLI command string:
  - app/verify/page.tsx#L124
  - app/verify/page.tsx#L126
  - app/verify/page.tsx#L137
- In this repository CLI parser, only `sign-manifest` is wired; no `verify` subcommand is exposed in `main.py`:
  - main.py#L86
  - main.py#L96
- Cryptographic verification exists in code (`verify_receipt`) and works programmatically, but is not executed by the hosted viewer UI:
  - core/audit.py#L417
  - core/audit.py#L439

#### 3. Medium: "Every AI action" signed receipt is true on `/v1/audit`, not on `/v1/evaluate`

- `/v1/audit` logs and returns `receipt` in response:
  - bridge/fastapi_wrapper.py#L1150
  - bridge/fastapi_wrapper.py#L1175
- `/v1/evaluate` returns decision metadata but no `receipt` field:
  - bridge/fastapi_wrapper.py#L969
  - bridge/fastapi_wrapper.py#L978
- Therefore universal signed-receipt coverage depends on clients using `/v1/audit` rather than `/v1/evaluate`.

#### 4. Medium: ISO/IEC 42001 mapping artifacts are not materially present as an auditable control matrix

- Technical controls relevant to 42001 intent exist (decision logging model, signed receipts, policy controls), but no explicit in-repo 42001 mapping matrix was identified during audit:
  - prisma/schema.prisma#L131
  - core/audit.py#L352
  - core/audit.py#L417
- Outcome: partial alignment by implementation, weak alignment by governance evidence/documentation.

### Verified Controls That Are Correct

- Cryptographic receipt generation/verification implementation is present and canonicalized for machine verification:
  - core/audit.py#L352
  - core/audit.py#L367
  - core/audit.py#L406
  - core/audit.py#L417
- Evidence export includes receipt + policy hash + payload hash fields suitable for downstream verifier tooling:
  - app/api/evidence/route.ts#L47
  - app/api/evidence/route.ts#L48
  - app/api/evidence/route.ts#L49

### Compliance Verdict (Current State)

- 30-day retention functionality (Hosted Pro/Enterprise): **Not demonstrated as enforced** in hosted DB paths from audited code.
- Independent validation via Receipt Viewer: **Not met** (viewer is structural inspection, not cryptographic verification).
- ISO/IEC 42001 mapping: **Partially met technically, not met as auditable governance mapping**.
- "Every AI action" signed receipt: **Partially met** (`/v1/audit` yes, `/v1/evaluate` no).

### Recommended Remediations

1. Implement and document a hosted audit-log retention enforcement job (e.g., scheduled `auditLog.deleteMany` by plan-specific window) and expose operational evidence.
2. Add server-side receipt verification endpoint (or signed client verifier bundle) used directly by the Receipt Viewer UI; do not rely on a non-existent CLI path in this repo.
3. Harmonize retention claims across pricing/docs/privacy/export metadata (single source of truth).
4. Either deprecate `/v1/evaluate` for compliance-sensitive flows or add signed receipt emission there.
5. Publish an explicit ISO/IEC 42001 control mapping matrix linking controls, code artifacts, tests, and operational ownership.

---

## Addendum: Production Functionality Audit — Hosted Site Routes, Security Headers, and API Client Patterns

Date: 2026-04-30
Scope: Route reachability (all 19 declared core routes), Nginx / edge proxy configuration, security header coverage (HSTS, CSP), and client-side API call patterns including 401 handling, token refresh, and centralized request helper.

---

### Section A — Route Inventory

**Finding 1 — 18 route files discovered; one expected route is absent**

A full scan of `app/api/` yielded 18 `route.ts` files:

| #   | Path                      | Methods            | Auth                      |
| --- | ------------------------- | ------------------ | ------------------------- |
| 1   | `/api/account`            | GET, PATCH, DELETE | Protected                 |
| 2   | `/api/account/export`     | POST               | Protected                 |
| 3   | `/api/auth/[...nextauth]` | GET, POST          | NextAuth                  |
| 4   | `/api/auth/register`      | POST               | Public                    |
| 5   | `/api/auth/verify-email`  | POST               | Public                    |
| 6   | `/api/cron/report-usage`  | POST               | Bearer token              |
| 7   | `/api/demo`               | POST               | None                      |
| 8   | `/api/demo/origins`       | GET, POST          | None                      |
| 9   | `/api/evidence`           | GET                | Protected                 |
| 10  | `/api/health`             | GET                | Admin (prod) / Open (dev) |
| 11  | `/api/keys`               | GET, POST          | Protected                 |
| 12  | `/api/keys/[id]`          | DELETE, PATCH      | Protected                 |
| 13  | `/api/logs`               | GET                | Protected                 |
| 14  | `/api/policy`             | GET, PUT           | Protected                 |
| 15  | `/api/settings`           | GET, PATCH         | Protected                 |
| 16  | `/api/stripe/checkout`    | GET, POST          | Session                   |
| 17  | `/api/stripe/webhook`     | POST               | Stripe-sig                |
| 18  | `/api/webhooks/stripe`    | POST               | Stripe-sig                |

Total confirmed: **18 routes**. If a 19th was declared, it is not present in the `app/api/` tree. No `route.ts` file was found for it. This represents a discrepancy that should be resolved against the product specification.

**Finding 2 — Protected-path list in middleware is narrower than the actual protected route set**

`middleware.ts` gates the following paths: `/dashboard`, `/api/keys`, `/api/logs`, `/api/evidence`, `/api/account`, `/api/settings`, `/api/policy`.

Routes that perform auth checks independently (inside the route handler via `getServerSession` or `getToken`) but are NOT in the middleware guard list:

- `/api/stripe/checkout` — 401 returned from route handler, not middleware
- `/api/health` — auth check inside handler (admin role only in production)
- `/api/cron/report-usage` — Bearer token check inside handler

These routes have a second line of defence but are bypassed by the middleware's early-return path for unauthenticated clients. If the route-handler-level check is ever removed, middleware would not catch it. Recommend adding all auth-bearing routes to the `protectedPaths` list in middleware.ts as a defence-in-depth measure.

---

### Section B — Nginx / Edge Proxy Configuration

**Finding 3 — No Nginx configuration exists in this repository**

The application is a Next.js 14 App Router project deployed via Vercel (confirmed by `vercel.json`) and optionally via Render (`render.yaml`). No Nginx configuration file was found anywhere in the repository tree.

SPA routing, reverse proxying, TLS termination, and HTTP→HTTPS redirection are handled entirely by the Vercel or Render edge runtime, not a self-managed Nginx instance.

Implications:

- For the hosted deployment: the audit assertion about Nginx proxying the React SPA does not apply. The platform (Vercel/Render) handles routing.
- For a self-hosted deployment: if an operator places Nginx in front of the Next.js process, they must supply their own Nginx configuration. None is shipped in the repository and none is referenced in deployment documentation (`docs/LAUNCH_GUIDE.md`, `docs/OPERATIONS_RUNBOOK.md`). A reference configuration should be added to deployment docs so operators do not misconfigure HTTPS termination, WebSocket upgrades, or proxy headers.

---

### Section C — Security Headers

**Finding 4 — HSTS is set but only in middleware; `next.config.js` duplicates four headers without HSTS for \_next/ paths covered by the `matcher` exclusion**

Header coverage by layer:

| Header                                                           | `next.config.js` `headers()`   | `middleware.ts` response    |
| ---------------------------------------------------------------- | ------------------------------ | --------------------------- |
| `X-Content-Type-Options: nosniff`                                | ✓                              | ✓                           |
| `X-Frame-Options: DENY`                                          | ✓                              | ✓                           |
| `Referrer-Policy: strict-origin-when-cross-origin`               | ✓                              | ✓                           |
| `Strict-Transport-Security: max-age=31536000; includeSubDomains` | ✓                              | ✓                           |
| `Permissions-Policy: camera=(), microphone=(), geolocation=()`   | ✓                              | ✗ (missing from middleware) |
| `Content-Security-Policy`                                        | ✗ (absent from next.config.js) | ✓                           |

`Permissions-Policy` is only set by `next.config.js` static headers, not by middleware. Requests that hit the middleware response path (all non-static paths) receive a complete header set only because `next.config.js` headers are applied before middleware response headers. However, if `next.config.js` `headers()` is ever removed or scoped, `Permissions-Policy` drops out silently.

**Recommendation:** Add `Permissions-Policy` to the middleware `response.headers.set(...)` block for defence-in-depth redundancy.

**Finding 5 — CSP uses `'unsafe-inline'` for `script-src` and `script-src-elem`**

Configured at middleware.ts#L113:

```
script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com
script-src-elem 'self' 'unsafe-inline' https://va.vercel-scripts.com
```

`'unsafe-inline'` bypasses the primary XSS protection that CSP provides. Any XSS vulnerability that injects a `<script>` tag inline would not be blocked. This is the current Next.js App Router default because RSC hydration scripts are inline, but the risk surface should be acknowledged.

**Recommendation:** Add a `nonce`-based CSP or switch to the planned Next.js `nonce` support to remove `'unsafe-inline'`. Until then, document this as an accepted risk in the threat model.

**Finding 6 — HSTS does not include `preload`**

`Strict-Transport-Security: max-age=31536000; includeSubDomains` is present, but the `preload` directive is absent. Without `preload`, browsers that have never visited the site are not protected until they receive the header on first visit (TOFU: Trust On First Use).

**Recommendation:** Add `; preload` and submit `app.aletheia-core.com` to the HSTS preload list if it is not already registered.

**Finding 7 — `Cross-Origin-Opener-Policy` (COOP) and `Cross-Origin-Resource-Policy` (CORP) are absent**

Neither header is set in `next.config.js` nor in middleware. Without COOP, the app window can be accessed via `window.opener` from cross-origin pages opened in the same browsing context group.

**Recommendation:** Add `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` to the middleware header block.

---

### Section D — Client-Side API Call Patterns: `request()` Helper and 401 Handling

**Finding 8 — No centralized `request()` helper exists; all client-side fetches are direct bare `fetch()` calls**

The audit question references an "api.js" file with a `request()` helper that auto-attaches auth headers and performs a single token-refresh attempt on 401. This file does not exist in the codebase. Client-side data fetching is performed with bare `fetch()` calls directly in each component:

| Component                                   | Call site(s)  |
| ------------------------------------------- | ------------- |
| `app/dashboard/keys/page.tsx`               | L49, L65, L90 |
| `app/dashboard/logs/page.tsx`               | L34           |
| `app/dashboard/settings/SettingsClient.tsx` | L39, L61, L89 |
| `app/dashboard/evidence/page.tsx`           | L21           |
| `app/dashboard/policy/page.tsx`             | L33           |
| `app/dashboard/usage/page.tsx`              | L36           |
| `app/components/UpgradeButton.tsx`          | L25           |

**Finding 9 — No client-side 401 detection, token-refresh attempt, or session-expiry redirect exists**

Not one of the `fetch()` call sites inspects `res.status === 401`. When a session expires mid-use, the response is either silently ignored (keys/page.tsx `fetchKeys` swallows the error in its catch block entirely) or treated as a generic failure with a toast message. The user is never automatically redirected to `auth/login`.

This means:

- A user whose session expires while on `/dashboard/keys` sees an empty key list with no error, not a login prompt.
- A user whose session expires while on `/dashboard/logs` sees "Failed to load audit logs." — no redirect, no re-auth prompt.

**Finding 10 — Auth is cookie-based (HttpOnly NextAuth session), so no `Authorization: Bearer` header attachment is required — but this must be explicitly documented**

The absence of `Authorization` headers in client-side `fetch()` calls is architecturally correct for this stack: NextAuth stores the session in a signed HttpOnly cookie (`next-auth.session-token`) that the browser attaches automatically. Client-side code cannot and should not attach bearer tokens.

However, this also means the audit framing of "auto-attached auth headers" is inapplicable to this architecture. The distinction matters for self-hosted operators who might integrate external API clients expecting Bearer tokens against these endpoints and receiving 401 without understanding why cookie-based auth is required.

---

### Section E — Recommended Remediations (Priority Order)

| Priority | Finding | Action                                                                                                                                                                                                                                                                                                     |
| -------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HIGH     | #8 / #9 | Create a centralized `lib/client-fetch.ts` `request()` wrapper that: (a) checks `res.status === 401` and calls `signIn()` (NextAuth re-auth flow) once before retrying; (b) checks `res.status === 403` and redirects to `/dashboard`; (c) is used by all dashboard components in place of bare `fetch()`. |
| HIGH     | #9      | In the interim, add a `res.status === 401 → router.push("/auth/login?callbackUrl=...")` check to at minimum `fetchKeys`, `fetchLogs`, and `handleExport` to prevent silent empty-state failures on session expiry.                                                                                         |
| MEDIUM   | #2      | Add all auth-bearing routes to the `protectedPaths` list in `middleware.ts`.                                                                                                                                                                                                                               |
| MEDIUM   | #5      | Implement nonce-based CSP to eliminate `'unsafe-inline'` from `script-src`.                                                                                                                                                                                                                                |
| MEDIUM   | #7      | Add `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Resource-Policy: same-origin` to the middleware header block.                                                                                                                                                                              |
| LOW      | #4      | Add `Permissions-Policy` to the middleware response headers to ensure it is set on all paths regardless of Next.js static header handling.                                                                                                                                                                 |
| LOW      | #6      | Add `preload` to HSTS and submit to the HSTS preload list.                                                                                                                                                                                                                                                 |
| LOW      | #3      | Add a reference Nginx configuration to deployment documentation covering HTTPS termination, proxy_pass, and required security headers for self-hosted operators.                                                                                                                                           |
| INFO     | #1      | Reconcile route count against the product specification to confirm whether a 19th route was planned and not yet implemented, or the route inventory is complete at 18.                                                                                                                                     |

---

## Addendum: Compliance and Data Safety Audit — PII Redaction, SHA-256 Audit Chain, and Machine-Verifiable Receipts

Date: 2026-04-30
Scope: PII detection and redaction before database/log persistence; SHA-256 hash-chain integrity across demo agentic decisions; TMR receipt structure and machine verifiability.

---

### Framing: "Memory Modules" and "Onboarding PII"

Aletheia-Core has no "Memory modules" in the agent-memory sense (episodic/semantic memory stores for conversation history). The product surfaces where user-supplied text enters the system are:

1. **Registration form** — name, email, password (handled by Next.js API routes + Prisma)
2. **API payload** — the `payload` field in `/v1/audit` and `/v1/evaluate` requests (handled by the Python pipeline)
3. **Demo form** — the `payload`, `origin`, and `action` fields submitted via `/api/demo`
4. **Audit reason/origin fields** — freeform strings produced by agents during decision processing

All findings below address PII handling in these surfaces.

---

### Section A — PII Redaction Before Persistence

#### Finding 1 — PASS: `redact_pii()` is applied unconditionally to all string audit log fields before write

The `redact_pii()` function is defined in `core/audit.py#L36`. It applies four compiled patterns:

| Pattern type | Regex                                                  | Replacement                             |
| ------------ | ------------------------------------------------------ | --------------------------------------- | --------------------------------- |
| Email        | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z                | a-z]{2,}`                               | `[REDACTED:email:<4-byte nonce>]` |
| US phone     | `(\+?1[-.\\s]?)?\(?\d{3}\)?[-.\\s]?\d{3}[-.\\s]?\d{4}` | `[REDACTED:phone:<4-byte nonce>]`       |
| SSN          | `\d{3}-\d{2}-\d{4}`                                    | `[REDACTED:ssn:<4-byte nonce>]`         |
| Credit card  | `(\d{4}[-\s]?){3}\d{4}`                                | `[REDACTED:credit_card:<4-byte nonce>]` |

Nonces are `os.urandom(4).hex()` — random per replacement, preventing rainbow-table reconstruction of redacted values from the placeholder.

`redact_pii()` is applied at `log_audit_event()` before the JSON record is written (`core/audit.py#L299`):

```python
for key in ("reason", "origin", "action"):
    if isinstance(record.get(key), str):
        record[key] = redact_pii(record[key])
```

PII redaction is also applied in the WebSocket stream at `core/ws_audit.py#L57` via `_redact_record()`.

There is **no configuration flag** that disables PII redaction — the `ALETHEIA_LOG_PII` override was removed (confirmed in `SECURITY.md#L95`).

#### Finding 2 — PASS: Raw payload content is never persisted to audit logs in active mode

`_hash_payload()` (`core/audit.py#L132`) stores only:

- `payload_sha256`: SHA-256 hex of the raw payload
- `payload_length`: character count

In non-active mode (shadow/debug), a sanitized `payload_preview` (max 120 chars, control characters stripped, truncated) is additionally stored. In active mode (`settings.mode == "active"`), `payload_preview` is suppressed.

This means raw user input — including any PII that appears in the payload — is never written to the audit log in production.

#### Finding 3 — MEDIUM: `receipt.prompt` contains the raw payload and is included in the receipt returned to the client

`build_tmr_receipt()` is called at the end of `log_audit_event()` with `prompt=payload` — the **original, unredacted** payload string:

```python
receipt = build_tmr_receipt(
    ...
    prompt=payload,   # ← raw payload, NOT the PII-redacted string
    ...
)
```

The receipt is returned in the API response as `record["receipt"]`. A client who submits a payload containing PII (e.g., `"Contact john@example.com to approve transfer"`) will receive that PII back in `receipt.prompt`. The audit log entry's `record_hash` covers `reason`/`origin`/`action` (which are redacted) — but the receipt itself is a client-facing artifact, not a log field.

**Risk:** If clients store or forward receipts, PII in `receipt.prompt` may be inadvertently persisted in client-side systems. The receipt prompt is also displayed in the demo UI (`app/demo/page.tsx#L752`).

**Remediation:** Pass `prompt=redact_pii(payload)` to `build_tmr_receipt()` so the signed canonical string and returned receipt contain the redacted form. The payload SHA-256 (which is signed) remains unchanged; the prompt field in the receipt becomes the redacted version.

#### Finding 4 — PASS: Registration-path PII (name, email, password) is never stored in audit logs

Registration and login are Next.js API routes that write to Prisma (PostgreSQL). They do not call `log_audit_event()`. Email is normalized to lowercase before DB insertion. Password is stored as bcrypt hash (`BCRYPT_COST=14`). There is no logging of plaintext credentials anywhere in the registration path.

#### Finding 5 — PASS: WebSocket audit stream strips payload fields and applies `redact_pii()` before broadcast

`core/ws_audit.py` `_STRIP_FIELDS` removes `payload_sha256`, `payload_preview`, `payload_length`, and `receipt` from all WebSocket broadcast records. After stripping, all remaining string values are passed through `redact_pii()` (`ws_audit.py#L57`). Live-stream subscribers cannot receive raw payload content or unscrubbed PII.

---

### Section B — SHA-256 Audit Chain Integrity

#### Finding 6 — PASS: Hash chain is implemented with `prev_hash` linked records and a `GENESIS` anchor

`log_audit_event()` maintains module-level state (`_prev_record_hash`, `_audit_seq`) under a `threading.Lock` (`_chain_lock`). Each record is built, its JSON is canonicalized with `sort_keys=True`, hashed as `SHA-256`, and the hash is stored in `record["record_hash"]`. Before writing, `record["prev_hash"]` is set to the previous record's hash (initialized to `"GENESIS"` at process start).

Chain properties:

- Sequential numbering via `_audit_seq` detects record gaps
- `prev_hash` links form a singly-linked chain; deletion or reordering of any record breaks the chain by making `record["prev_hash"]` not match the prior record's `record_hash`
- `sort_keys=True` canonicalization ensures field ordering does not affect hash
- The chain is **in-memory per process** — a server restart resets `_prev_record_hash` to `"GENESIS"` and `_audit_seq` to 0, creating a new chain segment beginning. Multi-instance deployments produce independent chains per instance.

#### Finding 7 — MEDIUM: Chain is in-process only — restart or multi-instance deployment silently resets the chain

There is no chain bootstrap step that reads the last `record_hash` from the audit log file at startup and initializes `_prev_record_hash` from it. Every process restart begins a new chain with `prev_hash = "GENESIS"`. A verifier auditing the log file will see multiple `GENESIS` entries — one per restart — which legitimately breaks the single-chain assumption.

Multi-instance deployments (Render/Vercel scaling out to multiple replicas) produce as many independent parallel chains as running instances — none linked to the others.

**Consequence:** Chain integrity is valid within a single process lifetime but cannot be verified across restarts or replicas. This is documented as an operational limitation but not disclosed to clients in the receipt or API response.

**Recommendation:** On startup, read the audit log file's last record and initialize `_prev_record_hash` from its `record_hash` field, so chains resume across restarts. For multi-instance deployments, adopt a shared distributed chain anchor (e.g., store the canonical `prev_hash` in Redis with CAS before each write).

#### Finding 8 — PASS: Policy hash is embedded in every audit record and receipt

Every record includes `policy_hash` (SHA-256 of `manifest/security_policy.json`), `manifest_fingerprint` (first 16 hex chars), and `policy_version`. These bind each audit decision to the exact policy manifest in effect at decision time, enabling retrospective verification that a decision was made under the correct policy.

In active mode, a missing manifest raises `RuntimeError` and prevents audit record creation entirely — fail-closed.

---

### Section C — TMR Receipt Machine-Verifiability

#### Finding 9 — PASS: Receipts are HMAC-SHA256 signed with a canonical string covering all decision-relevant fields

The canonical string for signing (`Receipt._canonical_string()`) covers:

```
decision | policy_hash | policy_version | payload_sha256
[| prompt:<value>]  ← optional, included when present
| action | origin | request_id | fallback_state | issued_at | decision_token | nonce
```

This canonical form prevents:

- **Decision substitution:** changing `DENIED` to `PROCEED` invalidates the signature
- **Policy substitution:** swapping in a different manifest hash invalidates the signature
- **Payload replay:** the `payload_sha256` binds the receipt to a specific payload; a valid receipt from a benign request cannot be reused for a malicious one (different SHA-256)
- **Action/origin replay:** `action` and `origin` are signed; a receipt for `fetch_data` cannot be presented as a receipt for `Transfer_Funds`

#### Finding 10 — PASS: `verify_receipt()` correctly uses `hmac.compare_digest` — timing-safe comparison

`core/audit.py#L417` `verify_receipt()`:

- Returns `False` if `ALETHEIA_RECEIPT_SECRET` is not set
- Returns `False` for `UNSIGNED_DEV_MODE` signatures
- Re-parses the receipt through `Receipt.model_validate()` to canonicalize field types before computing the expected HMAC
- Compares with `hmac.compare_digest(provided_sig, expected_sig)` — constant-time

#### Finding 11 — PASS: Dev/unsigned receipts are explicitly marked and `verify_receipt()` rejects them

When `ALETHEIA_RECEIPT_SECRET` is not set, `build_tmr_receipt()` returns `signature = "UNSIGNED_DEV_MODE"` and `warning = "Set ALETHEIA_RECEIPT_SECRET for production receipt signing."` at `core/audit.py#L407`. `verify_receipt()` explicitly returns `False` for this sentinel value.

#### Finding 12 — PARTIAL: Web receipt viewer performs structural inspection only — HMAC verification requires CLI

The `/verify` page (`app/verify/page.tsx`) performs client-side JSON parsing and field display only. It explicitly states:

> "Full cryptographic HMAC signature verification is available in the CLI — run `aletheia-audit verify` for on-chain HMAC validation."

**Risk:** Users who verify receipts via the web UI may believe they have performed cryptographic verification when they have only confirmed field presence. The UI has no "VALID SIGNATURE" / "INVALID SIGNATURE" indicator because the secret is server-side only.

**This is architecturally correct** — HMAC secrets cannot be exposed to browser clients. However, the UI should more prominently distinguish between "structural inspection passed" and "cryptographic signature verified" to prevent false assurance.

**Recommendation:** Add a prominent banner on the `/verify` page that says "Structural check only. To verify the HMAC signature, use the CLI or the server-side verification endpoint." and consider adding a `/api/verify` POST endpoint that accepts a receipt JSON and returns `{ valid: true/false }` using the server-side `verify_receipt()` function.

---

### Test Evidence (2026-04-30 run)

**`tests/test_pii_redaction.py` — 10 tests, all pass:**

| Test                                                   | Result |
| ------------------------------------------------------ | ------ |
| `test_email_redacted`                                  | ✓      |
| `test_phone_redacted`                                  | ✓      |
| `test_ssn_redacted`                                    | ✓      |
| `test_credit_card_redacted`                            | ✓      |
| `test_no_pii_unchanged`                                | ✓      |
| `test_multiple_pii_types`                              | ✓      |
| `test_hash_fingerprint_preserved` (random nonces)      | ✓      |
| `test_different_pii_different_hash`                    | ✓      |
| `test_log_pii_override_removed` (no disable flag)      | ✓      |
| `test_audit_event_redacts_pii_in_reason` (integration) | ✓      |

**`tests/test_enterprise.py` — 10 tests, all pass:**

| Test                                                                                   | Result |
| -------------------------------------------------------------------------------------- | ------ |
| `test_log_audit_produces_receipt`                                                      | ✓      |
| `test_payload_hashing_instead_of_redaction`                                            | ✓      |
| `test_tmr_receipt_signature_stable`                                                    | ✓      |
| `test_tmr_receipt_changes_with_different_decision`                                     | ✓      |
| `test_prompt_bound_and_backward_compatible`                                            | ✓      |
| `test_allows_up_to_limit`, `test_reset_clears_state`, `test_separate_keys_independent` | ✓      |
| `test_double_encoded_safe`, `test_url_encoded_smuggling`                               | ✓      |

---

### Compliance Verdict (Data Safety)

| Assertion                                              | Verdict           | Notes                                                                       |
| ------------------------------------------------------ | ----------------- | --------------------------------------------------------------------------- |
| PII redacted before audit log write                    | **PASS**          | `reason`, `origin`, `action` fields scrubbed; no override flag              |
| Raw payload content not persisted in active mode       | **PASS**          | SHA-256 + length only                                                       |
| `receipt.prompt` is PII-free                           | **FAIL — MEDIUM** | Raw unredacted payload passed to `build_tmr_receipt(prompt=payload)`        |
| Registration PII not logged                            | **PASS**          | No `log_audit_event()` call in registration path; bcrypt-hashed password    |
| WebSocket stream PII-safe                              | **PASS**          | Fields stripped + redact_pii applied                                        |
| SHA-256 hash chain within process                      | **PASS**          | Linked `prev_hash` chain with GENESIS anchor                                |
| Hash chain survives restart / multi-instance           | **FAIL — MEDIUM** | Chain resets to GENESIS on restart; no cross-process continuity             |
| Receipt HMAC covers all decision fields                | **PASS**          | Canonical string includes decision, payload SHA, action, origin, timestamps |
| `verify_receipt()` uses timing-safe comparison         | **PASS**          | `hmac.compare_digest`                                                       |
| Dev receipts rejected by verifier                      | **PASS**          | `UNSIGNED_DEV_MODE` sentinel explicitly refused                             |
| Web receipt viewer performs cryptographic verification | **PARTIAL**       | Structural inspection only; HMAC requires CLI                               |

---

## Addendum: Conversion Funnel Audit — Post-Registration Navigation, User Isolation, and Rate-Limiting

Date: 2026-04-30
Scope: Post-registration navigation to onboarding/dashboard; blank-state vs. welcome-state for new users; user data isolation; "first project" creation (API key generation for a new account); rate-limiting on `/api/auth/register` and the login path during peak demo traffic.

---

### Framing: "Project Initialization" and "Permission Conflicts" in This Codebase

As with the previous audit's "resolve_provider_for_role" terminology, "Project Initialization" and "project permission conflicts" are orchestration-framework concepts that do not exist in Aletheia-Core. The product has no "projects" in the Git/SaaS workspace sense. The closest analogous lifecycle step is **first API key generation** — the action a new user performs after accepting TOS, verifying their email, and reaching the dashboard for the first time. All findings below address that lifecycle.

---

### Section A — Post-Registration Navigation

#### Finding 1 — PASS: Credentials registration route to `verify-email`, never to a blank state

Flow on successful registration (`/api/auth/register` POST → 201):

1. `app/auth/register/page.tsx#L57`: `router.push("/auth/verify-email")`
2. `/auth/verify-email` renders a static confirmation page: envelope icon, "Check your inbox", link expiry notice, CTA to `/auth/login`.
3. On email link click → `GET /api/auth/verify-email?token=&email=`:
   - Invalid/missing token → `redirect("/auth/error?error=InvalidToken")`
   - Expired token → `redirect("/auth/error?error=TokenExpired")`
   - **Success → `redirect("/auth/login?verified=true")`**
4. On `?verified=true` login page: `verified` flag is read by `LoginContent` and a "Verified" success state can be displayed to the user.
5. On successful credential sign-in: `router.push(callbackUrl)` where `callbackUrl` defaults to `"/dashboard"` (login/page.tsx#L10).

At no step does the flow navigate to a blank state. Every terminal node — error, expiry, success — has a defined UI destination.

#### Finding 2 — PASS: OAuth registration bypasses email verification and lands directly at `/dashboard`

- `authOptions.pages.newUser = "/dashboard"` (lib/auth.ts#L204) — NextAuth redirects new OAuth users here automatically.
- `createUser` event auto-verifies OAuth users immediately (lib/auth.ts#L233).
- `signIn(provider, { callbackUrl: "/dashboard" })` in both register and login pages uses `/dashboard` as the fallback.

No blank state; no email verification gate for OAuth users.

#### Finding 3 — PASS: Dashboard layout gate enforces auth; unauthenticated hits redirect to login, not blank state

`app/dashboard/layout.tsx` calls `requireAuth()` at server render time. `requireAuth()` redirects to `/auth/login` on any session failure (lib/server-auth.ts#L10). A partially-authenticated user reaching `/dashboard` directly cannot see a blank inner page — the outer layout redirects before children render.

#### Finding 4 — PASS: New-user dashboard shows a Welcome Banner with guided onboarding steps, not a zero-state blank page

`app/dashboard/page.tsx#L44` passes `isNewUser={keyCount === 0 && totalRequests === 0}` to `DashboardOverview`.

`DashboardOverview` (L170): `const [showWelcome, setShowWelcome] = useState(isNewUser)`.

When `isNewUser` is true, a `WelcomeBanner` renders with:

- "Welcome to Aletheia Core" heading
- Three-step checklist: Generate API Key → Try Live Demo → View Audit Logs
- Per-step completion indicators backed by live counts (keyCount, totalRequests, logCount)
- A dismissable progress bar

A brand-new user with zero keys, zero requests, and zero logs will see this banner — not an empty shell.

**Note — database failure fallback:** `app/dashboard/page.tsx#L28-40` wraps the Prisma queries in a try-catch that logs the error but continues rendering with all counts defaulting to 0. If the DB is down, the dashboard renders with `isNewUser=true` regardless of whether the user actually is new. In that scenario the WelcomeBanner appears for returning users too. This is cosmetically incorrect but not a blank-state or crash — and it degrades gracefully.

---

### Section B — User Isolation ("First Project Creation" / API Key Generation)

#### Finding 5 — PASS: API key creation is scoped to `session.user.id` — no cross-user data access is possible

`POST /api/keys` (app/api/keys/route.ts):

- Reads session via `getServerSession(authOptions)` → validates `session.user.id`
- Creates `prisma.apiKey` with `userId: session.user.id` (server-assigned, not client-supplied)
- `GET /api/keys` fetches only `where: { userId: session.user.id }`
- `DELETE /api/keys/[id]` fetches the key first and checks `apiKey.userId === session.user.id` before deleting

There is no route parameter or request body field that allows a user to supply `userId`. User isolation is enforced server-side at every key operation.

#### Finding 6 — PASS: New TRIAL user receives quota and plan from `getHostedPlanConfig`, not from client input

`POST /api/keys` calls `getHostedPlanConfig(session.user.plan)` to resolve quota limits — the plan comes from the server-side JWT claim, which is sourced from the DB and refreshed on a `CLAIM_REFRESH_MS` cadence. A user cannot self-assign a higher plan or quota by manipulating the request body.

#### Finding 7 — PASS: No permission conflict prevents a new user from generating their first key

A new TRIAL user (plan="TRIAL", role="USER") hits no RBAC block at the key generation route. The route enforces:

1. Session present (auth check)
2. Plan quota check via `getHostedPlanConfig`
3. Rate limit (via `consumeRateLimit` with action scoped to IP)

None of these blocks fire for a first-time key creation on a valid account. There is no "admin approval" gate, no waiting period, and no project-membership check.

---

### Section C — Rate-Limiting: Registration and Login Endpoints

#### Finding 8 — PASS: Registration endpoint has IP-based rate limiting (5 attempts / 1 hour)

Constants in `app/api/auth/register/route.ts`:

```
REGISTER_LIMIT  = 5
REGISTER_WINDOW_MS = 3_600_000 (1 hour)
```

Implemented via `consumeRateLimit({ action: "register", key: clientIp, limit: 5, windowMs: 3_600_000 })`.

On breach: HTTP 429 with `Retry-After` header and `{ error: "rate_limited", message: "Too many registration attempts. Try again later." }`. Structured, human-readable.

#### Finding 9 — PASS: Login endpoint has per-email brute-force rate limiting (5 failures / 15 minutes)

Login rate limiting is implemented in `lib/auth.ts` via `checkLoginRateLimit(email)` which queries `prisma.loginAttempt` — **distinctly from the registration `consumeRateLimit` function**. On 5 login failures for a given email within 15 minutes, `authorize()` returns `null` (NextAuth maps this to an "CredentialsSignin" error → user sees "Invalid email or password.").

Failures are recorded on: wrong password, user not found, unverified email is **not** recorded (see Finding 12 below). Successes clear the failure log via `clearLoginFailures()`.

#### Finding 10 — CONFIRMED: Login endpoint has NO IP-based rate limit — only per-email brute-force protection

`checkLoginRateLimit` is keyed by **email address**, not IP. A distributed attacker targeting many different email addresses from a single IP suffers no progressive throttle. Conversely, a single IP cannot be blocked by attacking valid accounts from different sources.

For the stated concern about **legitimate traffic not being prematurely throttled during peak demo periods**: this is a **non-issue** for normal users — the per-email counter only increments on _failures_, so a legitimate user signing in successfully will never approach the limit and their failures are cleared on success.

However, a targeted attacker could:

1. Enumerate all registered emails from another surface
2. Make one failed attempt per email per window, staying under the 5-attempt threshold
3. Never trigger the email-level rate limit while making unlimited total requests to the login endpoint

**Recommendation:** Add an IP-level `consumeRateLimit` call to `authorize()` in the CredentialsProvider (or to a middleware layer for `/api/auth/callback/credentials`) covering the aggregate request rate regardless of email target.

#### Finding 11 — PASS: Rate-limit implementation uses Serializable transactions — safe under concurrent peak load

`lib/rate-limit.ts` uses `Prisma.TransactionIsolationLevel.Serializable` for the `RateLimitEvent` upsert pattern, with automatic retry on `P2034` (serialization failure). Under burst demo traffic this prevents the check-then-insert window from being exploited by concurrent requests.

Serializable isolation does incur higher lock contention than `READ_COMMITTED`. Under heavy concurrent demo load this may produce elevated P2034 retry counts before allowing a request. This is acceptable for registration (low volume) but worth monitoring for the demo proxy's `consumeRateLimit` calls under viral traffic.

#### Finding 12 — MEDIUM: Unverified-email login does not record a failure attempt — timing-based account existence oracle

In `lib/auth.ts` `authorize()`:

```
if (!user.emailVerified) return null;   // ← no recordLoginFailure() call here
```

An attacker who registers an account but does not verify the email can probe the login endpoint with the correct password and observe that:

- Wrong password → failure recorded, consistent timing
- Correct password on unverified account → immediate `null` return, **no failure recorded**, slightly different timing/behavior

This is a minor account-existence oracle if timing differences are observable. It does not result in unauthorized access, but it leaks whether a given email+password combination is correct for an unverified account.

**Remediation:** Add `await recordLoginFailure(email)` before the `return null` in the `!user.emailVerified` branch, matching the behavior of the wrong-password path.

---

### Section D — Open-Redirect Tests

All 9 `resolveAuthRedirect` unit tests pass (vitest run, 2026-04-30):

| Test                                                         | Result |
| ------------------------------------------------------------ | ------ |
| returns baseUrl for empty input                              | ✓      |
| rejects protocol-relative redirects (`//evil.com`)           | ✓      |
| rejects backslash traversal in encoded relative paths        | ✓      |
| rejects encoded protocol-relative redirects (`/%2Fevil.com`) | ✓      |
| appends safe relative paths (`/dashboard`)                   | ✓      |
| rejects look-alike subdomain (origin equality, not prefix)   | ✓      |
| rejects userinfo-host smuggling (`user@evil/`)               | ✓      |
| accepts same-origin absolute URL                             | ✓      |
| rejects unparseable URL                                      | ✓      |

---

### Compliance Verdict (Conversion Funnel)

| Assertion                                                            | Verdict     | Notes                                                                      |
| -------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------- |
| Post-registration: no blank state                                    | **PASS**    | Credentials → verify-email → login → dashboard; OAuth → dashboard directly |
| Post-registration: welcome/onboarding banner for new users           | **PASS**    | WelcomeBanner with 3-step checklist and progress indicator                 |
| DB failure during dashboard load renders blank state                 | **PARTIAL** | Gracefully degrades with zero-counts; WelcomeBanner shows but no crash     |
| User isolation: API key scoped to session user                       | **PASS**    | userId sourced from server-side session only                               |
| First key generation: no permission conflict                         | **PASS**    | TRIAL plan quota is permitted; no RBAC gate                                |
| Registration rate limit (no premature throttle for legitimate users) | **PASS**    | 5 attempts/IP/hour — adequate for normal traffic                           |
| Login rate limit covers distributed IP attacks                       | **FAIL**    | Per-email only; no IP-level aggregate limit                                |
| Unverified-email login records failure attempt                       | **FAIL**    | Timing oracle: missing `recordLoginFailure()` in unverified branch         |
| Open-redirect contract (9 tests)                                     | **PASS**    | All 9 pass                                                                 |

---

## Addendum: Demo Experience Audit — Key-Supply Mode, Project Run / Chat Lifecycle, and Provider Fallback

Date: 2026-04-30
Scope: New-user "Key-Supply Mode" guidance; demo lifecycle error handling vs. silent failures; `resolve_provider_for_role` fallback logic; `/api/demo` and `/api/keys` experience from a zero-key account perspective.

---

### Framing: What "Key-Supply Mode" and "resolve_provider_for_role" Mean in This Codebase

The audit request uses terminology ("Key-Supply Mode", "Project Run", "Chat lifecycle", `resolve_provider_for_role`) that originates in multi-agent orchestration frameworks (e.g. AutoGen, CrewAI). **None of this terminology exists in the Aletheia-Core codebase.** Aletheia-Core is not a chat or project-runner framework — it is a safety audit and agentic governance engine. It evaluates payload/action pairs for policy compliance and issues cryptographic receipts; it does not orchestrate LLM provider selection, run projects, or conduct chat sessions on behalf of users.

This finding is structural: the product surface being audited is a Sovereign Audit API + developer dashboard, not a chat/agent-builder product. All findings below therefore address the closest analogous concerns within the actual codebase:

- "Key-Supply Mode" → does a new user with zero API keys receive clear guidance rather than silent failures?
- "Project Run lifecycle" → does the demo (the product's interactive trial experience) handle every error state gracefully?
- "resolve_provider_for_role fallback" → does the demo proxy fall back to a system default rather than crashing when user-scoped keys are absent?
- "Cannot run agent" crashes / 500 errors → are these present anywhere in new-user flows?

---

### Section A — New-User Zero-Key Experience

#### Finding 1 — PASS: Zero-key state renders a clear guidance panel, not an error

When a new user has no API keys, `/dashboard/keys` renders (app/dashboard/keys/page.tsx#L383):

```
No keys yet. Generate a trial key to get started.
```

The `fetchKeys` call on mount silently handles auth/network failure in the catch block and resolves to an empty array rather than throwing. There is no 500 error and no crash.

Usage page analogously renders (app/dashboard/usage/page.tsx#L112):

```
No API keys yet. Generate a trial key to start using the hosted API.
```

followed by a "Generate Trial Key" CTA link to `/dashboard/keys`.

Both empty-state messages are human-readable, actionable, and do not expose internal errors.

#### Finding 2 — PASS: Demo page requires no personal API key at all — system key is used throughout

The demo at `/demo` and `/api/demo` proxy route operate on the shared `ALETHEIA_DEMO_API_KEY` (server-side only). A new user with zero personal keys can run the full audit lifecycle from the demo without touching the key management UI. The key-supply path for the demo is entirely server-managed; no user-side key configuration is referenced or required.

#### Finding 3 — PASS: `/api/keys` POST for key generation returns structured error messages, not raw exceptions

app/api/keys/route.ts enforces:

- `session.user.id` check → 401 with `{ error: "unauthorized" }`
- `ALETHEIA_KEY_SALT` absent in production → `throw new Error(...)` caught by FastAPI's global exception handler → HTTP 500 (see Finding 7 below)
- Plan quota limit check → structured `{ error, message }` JSON, not an unhandled crash

No route in the key management surface returns an unstructured 500 or `Cannot run agent` message.

---

### Section B — Demo Lifecycle Error Coverage

The demo page implements a complete error-to-message mapping for every error state the proxy can return. Confirmed at app/demo/page.tsx:

| Error code / HTTP status                         | UI message shown to user                                                                                                                      |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `free_tier_exhausted` (402)                      | `result.message` (server-supplied: "You've used your N free Sovereign Audit Receipts. Upgrade to continue...") — with redirect to upgrade URL |
| `rate_limited` (429)                             | "Rate limit reached. Try again in Xs." (uses `Retry-After` header)                                                                            |
| `request_timeout` (AbortError client-side)       | "Request timed out. The backend may be starting up — try again in a few seconds."                                                             |
| `service_unavailable` / `demo_unavailable` (503) | "Audit service temporarily unavailable. The backend may be warming up — try again in a few seconds."                                          |
| All other / unknown errors                       | "Something went wrong. Please try again."                                                                                                     |

Every error state sets a visible badge labeled `ERROR` with a human-readable message. No error state results in a blank panel or unhandled exception visible to the user.

#### Finding 4 — PASS: Demo proxy has no silent-failure path that returns `decision: undefined` to the UI

Every proxy error surface returns a structured JSON object. `isError` at app/demo/page.tsx#L314 correctly identifies both `result.error` truthy (explicit error code) and `!decision` (upstream returned an unusual body without a `decision` field), covering both cases.

#### Finding 5 — PASS: Upstream 401 (demo key not in KeyStore) is mapped to `demo_unavailable` 503, not exposed as raw auth failure

When the Render backend ephemeral SQLite loses the demo key registration:

- app/api/demo/route.ts#L291 logs at error level
- Returns `{ error: "demo_unavailable", message: "Demo backend is temporarily unavailable. Please try again later." }` with status 503
- UI renders "Audit service temporarily unavailable."

No raw 401 body is forwarded to the browser; no internal error detail is exposed.

#### Finding 6 — PASS: Demo proxy falls back to a secondary backend URL when the primary returns 5xx

`backendCandidates` is `[BACKEND_BASE, BACKEND_FALLBACK_BASE]` (app/api/demo/route.ts#L188). When the primary returns 5xx, the loop continues to the Render fallback. This is the closest analogue to `resolve_provider_for_role` system-default fallback: the system has a hardcoded fallback host and does not require any user-configured provider to be present.

The `BACKEND_BASE` read order: `ALETHEIA_BACKEND_URL` → `ALETHEIA_BASE_URL` → `"https://api.aletheia-core.com"` (hardcoded default). A fresh deployment with no env vars explicitly set will resolve to the hardcoded canonical API URL without crashing.

---

### Section C — Identified Gaps and Silent Failure Risks

#### Finding 7 — MEDIUM: `ALETHEIA_KEY_SALT` absent in production causes unhandled 500 on key generation

In `app/api/keys/route.ts#L20-L23`, if `ALETHEIA_KEY_SALT` is not set in production, `hashKey()` throws `new Error("ALETHEIA_KEY_SALT must be set in production...")`. This exception is not caught inside the route handler — it propagates to Next.js's default error boundary, which returns an HTTP 500 with a generic error page, not a structured JSON error.

A new user attempting to generate their first API key on a misconfigured production deployment receives an unstructured 500 error with no guidance message.

**Remediation:** Wrap `hashKey()` in a try-catch inside the POST handler and return `secureJson({ error: "configuration_error", message: "Key generation is temporarily unavailable. Contact support." }, { status: 503 })` rather than letting the exception propagate.

#### Finding 8 — LOW: Demo `rate_limit` DB error returns `service_unavailable` (503) without guidance for rate-limit DB being temporarily unavailable

When the Prisma rate-limit DB itself fails (app/api/demo/route.ts#L146), the proxy returns:

```json
{
  "error": "service_unavailable",
  "message": "Demo is temporarily unavailable. Please try again shortly."
}
```

The UI renders this as "Audit service temporarily unavailable." This is correct. However, the `message` field from the server body is not surfaced in the UI error handler — the UI uses its own static fallback string rather than `result.message` for the `service_unavailable` case (app/demo/page.tsx#L623 shows fixed string, not `result.message`).

**Consequence:** Server-supplied contextual messages for 503 errors are silently discarded; the user always sees the generic warm-up message. Low impact for current messages but would suppress useful future per-error context.

**Remediation:** Change the `service_unavailable` branch in app/demo/page.tsx#L623 to `result.message || "Audit service temporarily unavailable. The backend may be warming up — try again in a few seconds."` to surface server-side context when provided.

#### Finding 9 — LOW: `quickRun` duplicates the full fetch-and-render logic from `runAudit`, creating two code paths that can diverge

`quickRun` (app/demo/page.tsx#L258) is a near-copy of `runAudit` (app/demo/page.tsx#L218). Both paths set the same state and handle the same HTTP status codes, but are separate functions. Any future change to error handling applied only to one path will create a user-visible inconsistency between the "quick run" button and the "run audit" submit path.

**Remediation:** Extract the shared fetch-and-setState logic into a shared `executeAudit(payload, origin, action)` helper and call it from both `runAudit` and `quickRun`.

---

### Compliance Verdict (Demo Experience)

| Assertion                                                     | Verdict                | Notes                                                                  |
| ------------------------------------------------------------- | ---------------------- | ---------------------------------------------------------------------- |
| Zero-key new user sees guidance, not errors                   | **PASS**               | Empty-state copy + CTA in keys and usage pages                         |
| Demo runs without user-configured keys                        | **PASS**               | Server-managed shared demo key                                         |
| Demo lifecycle: all error states have human-readable messages | **PASS**               | Full mapping at page.tsx#L617                                          |
| No `Cannot run agent` or unhandled crash in new-user flow     | **PASS** (conditional) | Except for Finding 7 (ALETHEIA_KEY_SALT misconfiguration)              |
| System default fallback when no user key present              | **PASS**               | Demo proxy: hardcoded default backend URL                              |
| `resolve_provider_for_role` logic                             | **NOT APPLICABLE**     | Architecture does not include provider selection or chat orchestration |
| Server-supplied 503 messages surfaced to UI                   | **FAIL**               | `result.message` not used for `service_unavailable` branch (Finding 8) |

---

## Addendum: Self-Hosted Engine Security Posture & Fail-Closed Verification

Date: 2026-04-30
Scope: Self-hosted engine feature parity vs hosted API; fail-closed behavior when policy manifest or detection rules become unavailable.

### Section A — Hosted / Self-Hosted Feature Parity

#### Confirmed Parity Controls (self-hosted = hosted API)

The following controls are implemented identically in the open-source engine and the hosted API path:

1. **Three-agent pipeline (Scout → Nitpicker → Judge):** All three agents are instantiated as module-level singletons and run for every request in both `/v1/evaluate` and `/v1/audit`:
   - bridge/fastapi_wrapper.py#L307
   - bridge/fastapi_wrapper.py#L308
   - bridge/fastapi_wrapper.py#L309

2. **Input hardening before agents:** NFKC + confusable collapse + zero-width strip + recursive Base64/URL decode applied before any agent call:
   - bridge/fastapi_wrapper.py#L920
   - bridge/fastapi_wrapper.py#L1048

3. **Semantic intent pre-filter:** `classify_blocked_intent()` runs before Scout/Nitpicker/Judge in `/v1/audit`:
   - bridge/fastapi_wrapper.py#L1051

4. **Ed25519 manifest signature verification:** Verified at Judge instantiation (module import) and on `load_policy()` via SIGUSR1 hot-reload:
   - agents/judge_v1.py#L204
   - bridge/fastapi_wrapper.py#L560

5. **Daily alias bank rotation:** Deterministic Fisher-Yates shuffle seeded by HMAC(date + manifest hash), applied at Judge init and reloads:
   - agents/judge_v1.py#L175

6. **Raw score / reason sanitization:** `_discretise_threat()` and `_sanitise_reason()` apply to all client responses:
   - bridge/fastapi_wrapper.py#L685
   - bridge/fastapi_wrapper.py#L700

7. **Degraded-mode fail-closed for privileged actions:** When rate limiter or decision store is degraded, any non-read-only action returns DENIED:
   - bridge/fastapi_wrapper.py#L1024
   - bridge/fastapi_wrapper.py#L1025

8. **Decision-store fail-closed:** `verify_policy_bundle()` and `claim_decision()` return `accepted=False` on store failure:
   - core/decision_store.py#L311
   - core/decision_store.py#L313
   - core/decision_store.py#L344
   - core/decision_store.py#L346

9. **Production startup gate:** `validate_production_config()` aborts startup (`sys.exit(1)`) if receipt secret, Redis, TLS, or mode requirements are not met:
   - bridge/fastapi_wrapper.py#L80
   - core/config.py#L367

#### Divergence: Self-Hosted Default Mode Is Shadow, Not Active

- Self-hosted operators configure `ALETHEIA_MODE` through environment/yaml. Default value is `"active"` per config:
  - core/config.py#L104
- However, shadow mode (`ALETHEIA_MODE=shadow`) is a documented operating option and the entire test suite defaults to it:
  - tests/conftest.py#L13
- In shadow mode, blocked decisions are overridden to PROCEED at line:
  - bridge/fastapi_wrapper.py#L1147
- This means a self-hosted engine misconfigured or deliberately run in shadow mode in a non-production environment will **not** enforce DENIED outcomes, even for restricted actions like `Transfer_Funds`.

---

### Section B — Fail-Closed: Manifest Lost or Unavailable

#### Finding 1 — Confirmed: Manifest loss at startup causes hard service refusal (fail-closed)

- Judge is instantiated as a module-level singleton at import time:
  - bridge/fastapi_wrapper.py#L310
- `load_policy()` calls `verify_manifest_signature()` before parsing policy:
  - agents/judge_v1.py#L204
- If manifest bytes are missing or tampered, `ManifestTamperedError` is raised and re-raised (not swallowed):
  - agents/judge_v1.py#L218
  - agents/judge_v1.py#L219
- `ManifestTamperedError` at module import propagates to the FastAPI application startup and fails the entire service — no routes are served.
- Valid scenarios raising `ManifestTamperedError`:
  - algorithm mismatch: manifest/signing.py#L205
  - key_id mismatch: manifest/signing.py#L208
  - key_version mismatch: manifest/signing.py#L212
  - manifest version drift: manifest/signing.py#L215
  - expiry metadata mismatch: manifest/signing.py#L218
  - grace period elapsed: manifest/signing.py#L233
  - payload hash mismatch: manifest/signing.py#L250
  - Ed25519 signature invalid: manifest/signing.py#L262

#### Finding 2 — Confirmed: Manifest loss mid-runtime causes Judge to return DENIED for all actions

- Non-`ManifestTamperedError` exceptions during `load_policy()` (e.g., FileNotFoundError, permissions) set `self.policy = None`:
  - agents/judge_v1.py#L220
  - agents/judge_v1.py#L222
- `verify_action()` with `self.policy is None` immediately returns `(False, "CRITICAL: No policy loaded. All actions blocked.")`:
  - agents/judge_v1.py#L248
  - agents/judge_v1.py#L249
- This means every subsequent action request is DENIED because `is_allowed=False` feeds the OR gate:
  - bridge/fastapi_wrapper.py#L1111
- **Confirmed fail-closed.**

#### Finding 3 — Confirmed: Missing manifest in active mode raises RuntimeError in audit logging

- `_policy_hash()` raises `RuntimeError` when manifest file is missing in active mode:
  - core/audit.py#L112
  - core/audit.py#L113
- This surfaces as an unhandled exception during `log_audit_event()`, caught by the global exception handler:
  - bridge/fastapi_wrapper.py#L583
  - bridge/fastapi_wrapper.py#L587
- Response is HTTP 500 with `{"decision": "ERROR"}`, which is neither PROCEED nor DENIED.
- **Risk:** An action sequence that reaches `log_audit_event()` after manifest deletion returns `ERROR`, not `DENIED`. This is fail-opaque rather than strictly fail-closed for the API response, though no PROCEED is emitted.

#### Finding 4 — Medium: Alias bank rotation silently degrades to predictable seed when manifest is missing

- `_rotate_alias_bank()` catches `FileNotFoundError` and substitutes `"no_manifest"` as the hash:
  - agents/judge_v1.py#L188
  - agents/judge_v1.py#L189
- Result: rotation seed becomes predictable (date + literal "no_manifest"), allowing an attacker to enumerate alias order during a manifest outage window.
- Semantic alias veto is still functional (same alias phrases), but daily rotation entropy is degraded.

---

### Section C — Fail-Closed: Detection Rules Unavailable

#### Finding 5 — Confirmed: Nitpicker static pattern bank is always in-process (no external dependency)

- The 24 blocked semantic patterns are hardcoded in `AletheiaNitpickerV2.BLOCKED_PATTERNS` (class attribute):
  - agents/nitpicker_v2.py#L36
- Embeddings are computed from the local model on first call (lazy init). If the model file is unavailable, encoding raises an exception that propagates as a pipeline failure (HTTP 500 from global exception handler), not a PROCEED.

#### Finding 6 — Confirmed: Qdrant extended pattern lookup is fail-open by design

- `_safe_semantic_lookup()` catches all Qdrant errors and returns `degraded=True, matches=[]`:
  - agents/nitpicker_v2.py#L208
  - agents/nitpicker_v2.py#L212
- Qdrant is only queried when the static rule bank does NOT block. If Qdrant fails, the result falls through to the static result.
- The static 24-pattern bank is the documented safety floor in this design.
- A payload that would only be caught by Qdrant (not by the static 24 patterns) will reach PROCEED if Qdrant is unavailable. This is an accepted trade-off documented in the architecture.

#### Finding 7 — Confirmed: Scout detection rules are fully in-process (no external dependency)

- All Scout patterns (`smuggling_prefixes`, `exfil_patterns`, `neutral_tokens`, `high_value_targets`) are hardcoded in `__init__`:
  - agents/scout_v2.py#L14
  - agents/scout_v2.py#L56
- No network call or file load is required. Scout cannot lose its rules mid-runtime.

---

### Section D — Test Suite Evidence: Shadow Mode Test Failures Reveal a Real Fail-Open Gap

Three tests fail in the standard test run because the test suite runs in shadow mode (`ALETHEIA_MODE=shadow`, set in tests/conftest.py#L13) while the tests assert `DENIED` outcomes for restricted actions:

| Test                                  | Expected | Actual (shadow) | Root Cause                          |
| ------------------------------------- | -------- | --------------- | ----------------------------------- |
| `test_restricted_action_id_denied`    | DENIED   | PROCEED         | shadow mode overrides Judge veto    |
| `test_semantic_bypass_attempt_denied` | DENIED   | PROCEED         | shadow mode overrides semantic veto |
| `test_exfil_pattern_denied_at_api`    | DENIED   | PROCEED         | shadow mode overrides Scout match   |

- Shadow mode override logic: bridge/fastapi_wrapper.py#L1137 → bridge/fastapi_wrapper.py#L1147
- Shadow mode is correctly blocked in production (`ENVIRONMENT=production`): bridge/fastapi_wrapper.py#L1138

These test failures are not engine bugs — they are test assertions that incorrectly assume active mode when running in shadow mode. However, they prove that a self-hosted operator running `ALETHEIA_MODE=shadow` in a non-production environment receives **no enforcement** of any block decision.

---

### Compliance Verdict (Self-Hosted)

| Assertion                                                         | Verdict                                                 | Notes                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| Fail-closed on manifest tamper at startup                         | **PASS** — fails service entirely                       | ManifestTamperedError propagates         |
| Fail-closed on manifest loss mid-runtime (Judge)                  | **PASS** — all actions DENIED                           | policy=None branch                       |
| Fail-closed on manifest loss mid-runtime (audit log, active mode) | **PARTIAL** — returns ERROR not DENIED                  | HTTP 500 from audit path                 |
| Fail-closed on Qdrant loss                                        | **PARTIAL** — static 24-pattern floor only              | documented fail-open for Qdrant          |
| Fail-closed in shadow mode                                        | **FAIL** — all blocks overridden to PROCEED             | by design; no enforcement in shadow mode |
| Detection rules require no external service                       | **PASS** — Scout + Nitpicker static patterns in-process |                                          |
| Alias rotation degrades gracefully                                | **PARTIAL** — predictable seed when manifest missing    | agents/judge_v1.py#L189                  |

### Recommended Remediations

1. Replace `ERROR` HTTP 500 on audit-path manifest loss in active mode with a hard `DENIED` response to remove the fail-opaque gap.
2. Add explicit startup check that aborts (`sys.exit(1)`) when `manifest/security_policy.json` is absent in active mode, not just when `ALETHEIA_MANIFEST_HASH` is set.
3. In `_rotate_alias_bank()`, treat `FileNotFoundError` as a fatal condition in active mode rather than silently substituting `"no_manifest"`, preserving rotation entropy.
4. Add a test fixture variant that forces `ALETHEIA_MODE=active` for the three API-level fail-closed tests, so the test suite validates active-mode enforcement separately from shadow-mode observability.
5. Document clearly in self-hosted deployment guides that `ALETHEIA_MODE=shadow` disables enforcement and must not be used for agentic workflows where DENIED outcomes are relied upon.

---

## Source 2: FINAL_AUDIT_REPORT_2026-04-30.md

# Aletheia Core — Final Comprehensive Audit Report

**Date:** 2026-04-30
**Scope:** All source code in `/workspaces/aletheia-core` as of this date.
**Checklist categories:** basic-review, bug-hunt, owasp-security, performance-review,
accessibility-audit, architecture-review, dependency-audit, refactoring-guide, test-coverage.
**Method:** Static analysis, dynamic test execution (1 144 pytest tests, 9 vitest tests),
grep-based pattern matching, schema inspection, and manual code review.

---

## 1. Basic Review

| Item                                                  | Verdict | Notes                                                                                                   |
| ----------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------- |
| Code compiles / imports cleanly                       | PASS    | `python -m pytest --co -q` collects 1 144 tests with no import errors.                                  |
| README reflects actual entry points                   | PASS    | `app.py`, `main.py`, and Docker entry points match documented usage.                                    |
| Makefile targets functional                           | PASS    | `make lint`, `make test`, `make docker-build` all present.                                              |
| No committed secrets                                  | PASS    | `.env` files absent; `.gitignore` covers `.env*`.                                                       |
| Logging present at key decision points                | PASS    | `log_audit_event()` called on every PROCEED / DENIED path.                                              |
| No dead `print()` / debug statements in hot path      | PARTIAL | `economy/` module contains several `print()` calls used for diagnostics rather than structured logging. |
| File naming consistent                                | PASS    | `snake_case` throughout Python; `PascalCase` React/TS components.                                       |
| `pyproject.toml` / `package.json` versions consistent | PASS    | Both maintained; `pip-compile --generate-hashes` used for `requirements.txt`.                           |

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

| OWASP Category                          | Verdict | Detail                                                                                                                                                                                                                                                                                                      |
| --------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A01 Broken Access Control**           | PARTIAL | `middleware.ts` protects a subset of routes. The `protectedPaths` list is narrower than the actual protected route tree; routes not in the list rely solely on session checks inside the route handler. No CSRF protection on mutation endpoints (next-auth CSRF is JWT-based but no double-submit cookie). |
| **A02 Cryptographic Failures**          | PARTIAL | Ed25519 manifest verification, HMAC-SHA256 receipts, hash-pinned dependencies: all correct. **Gap:** `receipt.prompt` returns unredacted payload (BUG-04). `ALETHEIA_ALIAS_SALT` absent → alias bank rotation degrades to plain SHA-256 with predictable seed.                                              |
| **A03 Injection**                       | PASS    | All Python input goes through Pydantic `strict` validation with `extra="forbid"`. Input hardening normalises NFKC, strips zero-width chars, recursively URL/Base64 decodes, and collapses confusable homoglyphs before agent analysis. SQL: Prisma ORM (parameterised).                                     |
| **A04 Insecure Design**                 | PASS    | Tri-agent fail-closed pipeline, replay defence, drift detection, degraded-mode gate. Each agent independently deny-capable.                                                                                                                                                                                 |
| **A05 Security Misconfiguration**       | PARTIAL | CSP uses `'unsafe-inline'` for `script-src` (Next.js RSC limitation). COOP and CORP headers absent. HSTS missing `preload` directive. `Permissions-Policy` defined only in `next.config.js` headers, not in `middleware.ts` response, so it is absent from API-route responses.                             |
| **A06 Vulnerable Components**           | PARTIAL | Python `requirements.txt` hash-pinned via `pip-compile --generate-hashes` ✓. npm packages use `^` semver ranges — transitive float is possible (see §7). `starlette 1.0.0` is a brand-new major release; compat impact not yet validated.                                                                   |
| **A07 Identification & Authn Failures** | PARTIAL | BCRYPT cost 14 ✓. Per-email login rate limit (5/15 min) ✓. **Gaps:** No IP-level aggregate rate limit on login. Timing oracle in unverified-email branch (BUG-03).                                                                                                                                          |
| **A08 Software Integrity Failures**     | PASS    | Ed25519 manifest signature, hash-pinned wheels, Dockerfile `COPY --chown`.                                                                                                                                                                                                                                  |
| **A09 Logging & Monitoring**            | PASS    | `log_audit_event()` on every decision, TMR receipt, OpenTelemetry traces, 90-day retention setting documented.                                                                                                                                                                                              |
| **A10 SSRF**                            | PASS    | Demo proxy enforces protocol allowlist (`https://` only) and domain allowlist; no raw URL pass-through.                                                                                                                                                                                                     |

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

| Check                                          | Verdict      | Notes                                                                                                                                                                      |
| ---------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Interactive elements have semantic roles       | PARTIAL      | `<button>` used correctly throughout. Dismissible banners have `aria-label`. Nav landmark present. Missing: `<main>` landmark on some pages.                               |
| Form inputs have associated `<label>` elements | PARTIAL      | Settings, register, login forms have labels. Demo payload `<textarea>` uses placeholder text only — no `<label>` element (fails WCAG 2.1 SC 1.3.1).                        |
| Live regions for dynamic content               | PARTIAL      | Auth forms use `role="alert"`. Demo results panel uses `aria-live="polite"`. Audit log table updates do not use a live region — screen readers will not announce new rows. |
| Focus management after navigation              | NOT VERIFIED | No Playwright or axe-core tests. Focus restoration after modal open/close not verified.                                                                                    |
| Keyboard navigation                            | PARTIAL      | Standard HTML elements are keyboard-accessible. Custom dropdown menus and the demo control panel not verified for trap focus / `Escape` key support.                       |
| Colour contrast                                | NOT VERIFIED | No automated contrast check in CI. `globals.css` uses CSS custom properties; values not spot-checked in this audit.                                                        |
| Images have `alt` text                         | PASS         | `<Image>` components inspected; decorative images use `alt=""`.                                                                                                            |
| ARIA attributes are valid                      | PASS         | No invalid `aria-*` attribute patterns found in static analysis.                                                                                                           |

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

| Package                 | Version      | Notes                                                        |
| ----------------------- | ------------ | ------------------------------------------------------------ |
| `fastapi`               | 0.135.1      | Current stable                                               |
| `starlette`             | 1.0.0        | **RISK:** Brand-new major version; breaking changes possible |
| `pydantic`              | 2.12.5       | Current stable                                               |
| `cryptography`          | 46.0.5       | Current stable                                               |
| `sentence-transformers` | 5.3.0        | Current stable                                               |
| `qdrant-client`         | 1.17.1       | Current stable                                               |
| `redis`                 | 7.4.0        | Current stable                                               |
| `opentelemetry-sdk`     | 1.37.0       | Current stable                                               |
| `uvicorn`               | 0.41.0       | Current stable                                               |
| `asyncpg`               | 0.30.0       | Current stable                                               |
| `bcrypt`                | (transitive) | Version determined by `cryptography` extras                  |

All wheels are hash-pinned via `pip-compile --generate-hashes`. Supply-chain integrity is
strong. **Action required:** validate `starlette 1.0.0` compatibility with existing
middleware and exception handlers before launch.

### npm (package.json — `^` ranges)

| Package             | Declared       | Notes                                           |
| ------------------- | -------------- | ----------------------------------------------- |
| `next`              | 16.2.4 (exact) | Exact pin for Next.js — good practice           |
| `next-auth`         | ^4.24.13       | Patch float acceptable                          |
| `@prisma/client`    | ^5.22.0        | Minor float acceptable                          |
| `bcryptjs`          | ^3.0.3         | Minor float acceptable; cost=14 in code ✓       |
| `stripe`            | ^22.0.1        | Minor float; Stripe SDK is stable               |
| `resend`            | ^6.11.0        | Minor float                                     |
| `@vercel/analytics` | ^2.0.1         | Low risk                                        |
| `zod`               | (transitive)   | Version not pinned; Zod v4 is a breaking change |

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

| Metric          | Value                                                                      |
| --------------- | -------------------------------------------------------------------------- |
| Tests collected | 1 144                                                                      |
| Passed          | 1 119                                                                      |
| Failed          | **10**                                                                     |
| Skipped         | 16                                                                         |
| Failure rate    | 0.87% overall; **80% failure rate** in `test_api.py` enforcement sub-suite |

**Root cause of all 10 failures:**

| Failures        | Root Cause                                                                                   |
| --------------- | -------------------------------------------------------------------------------------------- |
| 8 (shadow mode) | `ALETHEIA_MODE=shadow` in `conftest.py` → all DENIED flipped to PROCEED                      |
| 2 (health 503)  | `manifest/security_policy.json` and Redis not configured in CI → readiness probe returns 503 |

**Coverage Gaps:**

- **Active-mode enforcement path not tested.** No test runs with `ALETHEIA_MODE=active`. The full production enforcement contract is unverified in CI.
- **No integration tests for API key generation error handling.** `hashKey()` throw on missing `ALETHEIA_KEY_SALT` has no test.
- **No tests for SHA-256 chain bootstrap.** Chain continuity across restarts is untested.
- **No tests for 401 session expiry in dashboard fetch paths.** TypeScript component tests use mocks only.
- **Timing oracle not tested.** No test asserts that the login path has equal timing for verified vs. unverified accounts.

### 9.2 TypeScript — vitest

| Metric          | Value |
| --------------- | ----- |
| Tests collected | 9     |
| Passed          | 9     |
| Failed          | 0     |

**Coverage Gaps:**

- Tests cover string-utility and schema-validation helpers only.
- Zero coverage of dashboard components, API routes, auth flows, or middleware.
- No Playwright / axe-core accessibility tests in CI.

---

## Summary Risk Matrix

| ID        | Severity    | Category                   | Title                                              |
| --------- | ----------- | -------------------------- | -------------------------------------------------- |
| BUG-01    | 🔴 CRITICAL | Bug / Test-Coverage        | Shadow mode disables enforcement in all tests      |
| BUG-02    | 🟠 HIGH     | Bug / OWASP A05            | `hashKey()` crashes on missing `ALETHEIA_KEY_SALT` |
| BUG-03    | 🟠 HIGH     | Bug / OWASP A07            | Timing oracle on unverified-email login branch     |
| BUG-04    | 🟠 HIGH     | Bug / OWASP A02            | `receipt.prompt` exposes unredacted PII            |
| RF-02     | 🟠 HIGH     | Refactoring / Architecture | No `401` handling in any dashboard fetch call      |
| BUG-05    | 🟡 MEDIUM   | Bug / Architecture         | Audit chain resets to GENESIS on restart           |
| OWASP-A05 | 🟡 MEDIUM   | Security                   | `unsafe-inline` CSP; missing COOP/CORP headers     |
| OWASP-A01 | 🟡 MEDIUM   | Security                   | `protectedPaths` list narrower than actual routes  |
| BUG-07    | 🟡 MEDIUM   | Bug / Test                 | Health endpoint always 503 in CI                   |
| BUG-06    | 🟡 MEDIUM   | Bug / UX                   | `service_unavailable` discards error message       |
| DEP-01    | 🟡 MEDIUM   | Dependency                 | `starlette 1.0.0` compatibility not validated      |
| RF-01     | 🟢 LOW      | Refactoring                | Duplicate `quickRun`/`runAudit` logic              |
| RF-04     | 🟢 LOW      | Refactoring                | `print()` in `economics/` should use logger        |
| A11Y-01   | 🟢 LOW      | Accessibility              | Demo textarea missing `<label>`                    |
| A11Y-02   | 🟢 LOW      | Accessibility              | Audit log table missing `aria-live` region         |
| PERF-01   | 🟢 LOW      | Performance                | Sequential Prisma queries in dashboard page        |

---

## Source 3: LAUNCH_READINESS_2026-04-30.md

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

---

## Source 4: PHASED_FIX_PLAN_2026-04-30.md

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

:\*\*

### P1-1: Fix shadow-mode test contamination (BUG-01)

**Priority CRITICAL
**Effort:** 2 h
**Files:\*\* `tests/conftest.py`

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
       { status: 500 },
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
     timeoutMs = 10_000,
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

| ID   | Severity | Phase | Effort | Owner |
| ---- | -------- | ----- | ------ | ----- |
| P1-1 | CRITICAL | 1     | 2 h    | —     |
| P1-2 | HIGH     | 1     | 0.5 h  | —     |
| P1-3 | HIGH     | 1     | 0.5 h  | —     |
| P1-4 | HIGH     | 1     | 1 h    | —     |
| P1-5 | MEDIUM   | 1     | 1 h    | —     |
| P2-1 | HIGH     | 2     | 2 h    | —     |
| P2-2 | MEDIUM   | 2     | 3 h    | —     |
| P2-3 | MEDIUM   | 2     | 4 h    | —     |
| P2-4 | MEDIUM   | 2     | 0.5 h  | —     |
| P2-5 | LOW      | 2     | 0.5 h  | —     |
| P2-6 | HIGH     | 2     | 3 h    | —     |
| P2-7 | LOW      | 2     | 0.25 h | —     |
| P3-1 | LOW      | 3     | 0.5 h  | —     |
| P3-2 | LOW      | 3     | 1 h    | —     |
| P3-3 | LOW      | 3     | 2 h    | —     |
| P3-4 | LOW      | 3     | 0.5 h  | —     |
| P3-5 | MEDIUM   | 3     | 1 h    | —     |
| P3-6 | LOW      | 3     | 1 h    | —     |
| P3-7 | MEDIUM   | 3     | 2 h    | —     |

**Phase 1 total effort estimate:** ~5 hours
**Phase 2 total effort estimate:** ~14 hours
**Phase 3 total effort estimate:** ~8 hours
**Grand total:** ~27 engineer-hours
