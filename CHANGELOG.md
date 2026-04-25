# Changelog

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.9.1] — 2026-04-22

### Launch Notes
- **Production status flip**: Hosted API status is now `live`; the under-construction banner is hidden when `STATUS.hostedApi === "live"`.
- **Public pricing model update**: Introduced launch-tier terminology and constants for `free`, `scale`, `pro`, and `payg` in `lib/site-config.ts`.
- **Stripe tier expansion**: Checkout and webhook flows now support Scale/Pro/PAYG tier mapping with dedicated env-based Stripe price IDs.
- **Free-tier gate UX**: Demo upgrade flow now returns a paid-upgrade response (`402`) with an upgrade URL when free-tier usage is exhausted.
- **Pricing UX additions**: Added trust messaging and a PAYG section on pricing page, plus an interactive ROI calculator component.
- **Terminology migration**: Public UI/legal copy updated from generic request language to Sovereign Audit Receipts / verified decisions.

### Migration Notes
- **New Stripe env vars**: add `STRIPE_SCALE_PRICE_ID`, `STRIPE_PAYG_PRICE_ID`, and optional `STRIPE_SCALE_PRICE_AMOUNT`, `STRIPE_SCALE_CURRENCY`, `STRIPE_PAYG_CURRENCY`.
- **Deprecated naming**: `STRIPE_MAX_*` is no longer used by hosted checkout flows.

### Fixed
- **`asyncpg` dependency**: Added to `pyproject.toml` core dependencies and `requirements.txt`
  with hash pin. Resolves `ModuleNotFoundError` on Python 3.14 / Render production deploys
  using a Postgres decision store backend.
- **`ALETHEIA_MODE` startup validation**: Hardened parser now rejects whitespace-padded or
  slash-delimited placeholder strings (e.g. `active / shadow / monitor`). Only `active`,
  `shadow`, or `monitor` are accepted; any other value exits at startup.
- **`ManifestTamperedError: key version mismatch`**: Documented that
  `ALETHEIA_MANIFEST_KEY_VERSION` must be set to `v1` to match the committed
  `manifest/security_policy.json.sig` and prevent startup failure on fresh deploys.
- **Frontend API route** (`app/api`): Fixed TypeScript route handler for Next.js 14
  app-directory routing.
- **Stale version strings in docs**: `docs/API_REFERENCE.md`, `docs/OPERATIONS_RUNBOOK.md`,
  and `docs/index.html` updated from stale `1.7.0` references to `1.9.1`.

---

## [1.9.0] — 2026-04-19

### Security Hardening (Enterprise)
- **Remove `ALETHEIA_API_KEYS` env-var fallback**: API key authentication is now
  exclusively via KeyStore (SQLite/Postgres). Setting `ALETHEIA_API_KEYS` in
  production causes a hard startup failure (`RuntimeError`); in development it
  logs a warning and is ignored.
- **Remove `X-Admin-Key` bypass**: All admin endpoints (`/v1/keys`, `/v1/rotate`,
  `/health` diagnostics) now use RBAC permission checks (`require_permission()`).
  The `X-Admin-Key` header and `ALETHEIA_ADMIN_KEY` env var are no longer used.
- **CORS wildcard pre-commit hook**: New `no-cors-wildcard` hook prevents
  `allow_origins = ["*"]` from reaching production code.
- **AST-based string concatenation bypass detection**: Sandbox now parses Python
  payloads as AST and detects `getattr(obj, 'sys' + 'tem')`, f-string attribute
  construction, and dynamic subscript patterns. Regex fallback for non-Python text.
- **Strict Base64 validation**: Rejects whitespace-fragmented Base64, validates
  charset/padding, and calls `base64.b64decode(validate=True)` as final check.
- **Enforce distributed decision store**: Production now requires Upstash Redis
  for the decision store. SQLite fallback is blocked with `sys.exit(1)`.
- **Remove PII logging override**: `ALETHEIA_LOG_PII` env var removed. PII is
  always redacted — no override path exists.
- **Proxy depth configuration warning**: Logs warning when `ENVIRONMENT=production`
  and `ALETHEIA_TRUSTED_PROXY_DEPTH` is at the default value of 1.

### Resilience
- **Rate limiter circuit breaker probe-through**: When the Redis circuit is open,
  ~10% of requests are allowed through as probes to detect recovery. Successful
  probes automatically close the circuit and clear degraded state.
- **Distributed login failure tracking**: Brute-force protection in the Next.js
  auth layer now uses PostgreSQL (`LoginAttempt` Prisma model) instead of an
  in-memory `Map`. Works across all server instances. Periodic cleanup of
  expired attempts every 60 seconds.

### Added
- **Prisma `LoginAttempt` model**: Tracks per-email login failures with
  `@@index([email, createdAt])` for efficient sliding-window queries.
- **19 new Phase 3 tests**: String concatenation bypass patterns (9 tests),
  malformed/invalid Base64 payloads (5 tests), X-Forwarded-For IP rotation
  detection (2 tests), circuit breaker probe-through (3 tests).

### Changed
- RBAC permissions: `KEYS_CREATE`, `KEYS_LIST`, `KEYS_REVOKE`, `KEYS_USAGE`,
  `SECRETS_ROTATE` now gate admin endpoints (previously `X-Admin-Key` header).
- CORS `allow_headers` changed from `X-Admin-Key` to `Authorization`.
- Test suite deduplicated: removed 5 duplicate tests across `test_hardening.py`
  and `test_swarm_1000bot.py`.

### Removed
- `ALETHEIA_API_KEYS` env-var authentication path
- `ALETHEIA_ADMIN_KEY` / `X-Admin-Key` header authentication
- `ALETHEIA_LOG_PII` env-var override
- `ALETHEIA_ALLOW_SQLITE_PRODUCTION` production opt-in for SQLite decision store

### Verified
- Full test suite: **1114 passed**, 16 skipped.
- Full test suite: **1028 passed**, 16 skipped.

## [1.8.0] — 2026-04-18

### Added
- **Qdrant Semantic Layer**: Nitpicker now queries Qdrant vector store for extended
  pattern matches after static pattern check. Fail-open on Qdrant errors — static
  patterns remain the safety floor. Block threshold: 0.60.
- **Symbolic narrowing** (`core/symbolic_narrowing.py`): Pre-filters payloads into
  coarse intent buckets (action × object) before vector search. Categories include
  `direct_exfiltration`, `policy_evasion`, `data_destruction`, `privilege_escalation`,
  `credential_theft`, `auth_bypass`, `code_execution`, `recon`, `hybrid_composite`.
- **Vector store wrapper** (`core/vector_store.py`): Thread-safe lazy Qdrant client
  with configurable timeout (120ms default), fail-open semantics, and payload-indexed
  collection bootstrap.
- **Semantic manifest schema** (`core/semantic_manifest.py`): Pydantic models for
  the semantic pattern manifest with threshold validation (0.0–1.0).
- **Index builder** (`scripts/build_semantic_index.py`): CLI to read manifest, verify
  Ed25519 signature, generate embeddings (BAAI/bge-small-en-v1.5), upsert to Qdrant,
  create snapshot, and output signed `index_receipt.json`.
- **NitpickerResult dataclass**: Structured result with `is_blocked`, `reason`,
  `degraded`, `categories`, `top_match_id`, `top_match_score`, `source`.
- **Pipeline metadata**: Response now includes `semantic_degraded`,
  `semantic_categories_checked`, and `semantic_top_match_id` fields.
- **`ThresholdsConfig`**: Per-category cosine-similarity block thresholds
  (direct_exfiltration=0.86, policy_evasion=0.84, hybrid_composite=0.82,
  recon_alias=0.88) with `get_threshold_for_category()` fallback to 0.85.
- **`SemanticEntry`** (v2 schema): Strict category/severity literals,
  `EntryMetadata` with actions/objects/channels sub-object.
- **`validate_entries()`**: Duplicate ID detection on `SemanticManifest`.
- **`_safe_semantic_lookup()`**: Nitpicker method that wraps Qdrant call —
  120ms timeout, returns `{degraded, matches, error}`, NEVER raises.
- **`semantic_engine` block**: Audit receipt now includes structured block
  with `enabled`, `degraded`, `manifest_version`, `categories_checked`,
  `top_match` (id/score/threshold/category), and `error`.
- **Signed index receipt**: `build_semantic_index.py` outputs receipt with
  `manifest_hash`, `collection_name`, `vector_count`, `embedding_model`,
  `embedding_dim`, `distance_metric`, `qdrant_snapshot_id`, `built_at`,
  per-category `thresholds`, and optional Ed25519 signature.
- **51 tests** for semantic layer (symbolic narrowing, vector store,
  semantic manifest schema, thresholds, duplicate ID validation).
- **`qdrant-client>=1.9.0`** as optional dependency (`[semantic]`).

### Changed
- Nitpicker blocked pattern count: 19 → 24 (from v1.7.1 fix, now documented correctly).
- Nitpicker now loads category-specific thresholds from `SemanticManifest`
  instead of using hardcoded 0.60 block threshold.

### Verified
- Full test suite: **1018 passed** (967 existing + 51 new).

## [1.7.1] — 2026-04-18

### Fixed
- **Nitpicker semantic block now feeds pipeline decision**: `check_semantic_block()` result
  was computed but never consulted in PROCEED/DENIED gate. Payloads in the 0.45–0.55
  cosine-similarity band slipped through on early attempts and were only caught later by
  Scout's rotation-probing accumulator. All three agents now independently deny.
- **AGENTS.md accuracy**: Corrected blocked pattern count (18 → 19), updated pipeline
  flow diagram, and documented Nitpicker's deny capability.
- **README.md**: Updated test badge (957 → 967).

### Verified
- Full test suite: **967 passed**.

## [1.7.0] — 2026-04-13

### Added
- **Engineering blog**: New `/blog` index and statically generated `/blog/[slug]` post pages.
- **CLI docs page**: New `/cli` page covering manifest signing, operational commands, and troubleshooting.
- **Changelog page**: New `/changelog` page surfaced in app navigation.
- **Theme toggle**: Persistent dark/light mode selection in navigation and mobile drawer.
- **Environment variable guide**: Added `docs/ENVIRONMENT_VARIABLES.md` with local vs hosted requirements.

### Changed
- **Security debt fixes (7 findings)**:
  - SSRF host validation tightened in demo proxy.
  - Startup manifest hash pinning (`ALETHEIA_MANIFEST_HASH`).
  - Public `/health` minimized; admin diagnostics gated.
  - Audit log hash chaining (`seq`, `prev_hash`, `record_hash`).
  - ReDoS risk reduced in regex-heavy paths.
  - Production `NEXTAUTH_SECRET` guard strengthened.
  - Scout query history eviction improved with O(1) LRU behavior.
- **SEO and discovery**: Updated `robots.txt` and `sitemap.xml` generation for blog/changelog/cli routes.
- **Navigation/footer**: Added Blog/Changelog/CLI links across primary user-facing surfaces.
- **Dependency cleanup**: Removed unused Supabase helper files and related package references.

### Verified
- `next build` passes with 49 routes.
- Full test suite passes: **698 passed**.

## [1.6.3] — 2026-04-12

### Added — UX/UI Overhaul
- **Stripe checkout integration**: `/api/stripe/checkout` endpoint creates Stripe
  checkout sessions for Pro plan upgrades. `UpgradeButton` client component handles
  redirect flow. `site-config.ts` upgrade CTA now points to checkout (was `mailto:`).
- **Account settings page**: `/dashboard/settings` with display name editing,
  plan/billing display, upgrade CTA for Trial users, and sign out.
- **Settings API**: `PATCH /api/settings` for updating user display name.
- **Onboarding**: Welcome banner for new dashboard users (0 keys, 0 requests) with
  3-step guided flow (Generate Key → Try Demo → View Logs).
- **Mobile navigation**: Hamburger menu at ≤768px with full-screen drawer overlay.
- **Mobile dashboard**: Sidebar collapses to horizontal scrollable tabs on mobile;
  content area uses responsive padding.
- **Dashboard breadcrumbs**: Auto-generated from URL path segments.
- **Upgrade banner**: Shown on dashboard when Trial users reach ≥80% of monthly
  quota, with usage stats and one-click upgrade button.

### Changed
- **Pricing clarity**: Trial tier now shows "1,000 requests/month", Pro shows
  "100,000 requests/month, up to 10 API keys" (were vague "limited" / "higher").
- **Demo page CTAs**: Stronger conversion section with "Start Free Trial" primary
  CTA, "Sign In" secondary, and specific quota details.
- **WCAG contrast**: `--muted` color changed from `#6b7585` (3.5:1) to `#8b95a5`
  (4.5:1+ AA compliant against dark background).
- **Test count**: 689 → 697 (added security hardening and edge-case tests).

---

## [1.6.2] — 2026-04-10

### Security — Enterprise Hardening
- **Config validation**: All security thresholds validated at startup (range checks,
  logical consistency). Invalid thresholds now fail-fast with actionable errors.
- **HMAC-keyed API key hashing**: key_store now uses HMAC-SHA256 with
  `ALETHEIA_KEY_SALT` instead of plain SHA-256. Falls back with a logged warning.
- **SQLite file permissions**: Decision store and key store databases enforce
  `0o600` (owner read/write only) on creation.
- **Audit log path traversal protection**: `..` components in audit_log_path are
  rejected; audit log file permissions set to `0o600`.
- **Manifest fail-closed**: Missing `security_policy.json` in active mode now raises
  `RuntimeError` instead of silently returning `MANIFEST_MISSING`.
- **Timing oracle fix**: API key comparison now evaluates ALL keys before returning
  (no short-circuit) to prevent timing side-channel attacks.
- **Proxy depth validation**: `ALETHEIA_TRUSTED_PROXY_DEPTH` validated to 0–5 range
  at startup. XFF ignored entirely when depth=0.
- **Rate limiter hardening**: Circuit breaker adds random jitter to prevent
  thundering herd on recovery. Redis URL no longer logged.
- **Embedding input validation**: `encode()` rejects empty input, >1000 texts,
  or >500 KB total text to prevent OOM/hang.
- **CSP + Permissions-Policy headers**: Added to FastAPI middleware and vercel.json.
- **Sandbox response redaction**: Sandbox block responses no longer leak matched
  pattern names to clients.
- **PROCEED response hardening**: Removed `reasoning` field from PROCEED responses
  to prevent veto-logic leakage.
- **YAML config bomb protection**: Config loader enforces 100 KB file size limit.
  YAML parse errors are now logged explicitly instead of silently swallowed.
- **Container hardening**: Dockerfile adds HEALTHCHECK, `--timeout-keep-alive`,
  `--no-create-home`, and restrictive `/app/data` permissions.
- **Config type coercion**: Invalid env var types for floats/ints now logged with
  actionable errors instead of crashing with bare ValueError.

---

## [1.6.0] — 2026-04-08

### Added
- **Trial API Key system**: SQLite-backed key store with SHA-256 hashing,
  monthly quota enforcement, and billing period auto-reset (`core/key_store.py`)
- Key management endpoints: `POST /v1/keys`, `GET /v1/keys`,
  `DELETE /v1/keys/{id}`, `GET /v1/keys/{id}/usage` — all admin-key protected
- Dashboard: Trial Keys page with backend integration, quickstart curl example
- Dashboard: Usage visibility page with progress bars and plan metadata
- Next.js API proxy routes (`/api/keys`) to keep admin key server-side
- 40 new tests: 26 key store unit tests + 14 quota enforcement integration tests

### Changed
- `_check_api_key` now supports two-tier auth: env keys (no quota) + key store
  keys (trial/pro with monthly quota)
- CORS updated to allow DELETE method and X-Admin-Key header
- Middleware updated with method allowlists for `/v1/keys` paths
- Dashboard nav reordered; overview cards updated with trial language
- Logs page replaced with honest placeholder (removed fake mock data)
- Version bumped to 1.6.0

### Security
- Trial keys are SHA-256 hashed at rest; raw key returned only once at creation
- Admin endpoints require dedicated `ALETHEIA_ADMIN_KEY` (constant-time compare)
- Quota exceeded returns 429 with Retry-After header

---

## [1.5.3] — 2026-04-08

### Fixed
- CI: `InMemoryRateLimiter` and `DecisionStore` no longer mark themselves
  degraded when Upstash Redis is unavailable — local fallbacks are functional
- Three `test_redteam_adversarial` tests now pass without Upstash env vars

### Changed
- Site/dashboard/docs: pricing restructured to 4 tiers (Community, Hosted
  Trial, Hosted Pro, Services) with explicit prices
- Nav simplified to Demo, Docs, GitHub, Pricing, Services
- Dashboard keys pages updated to trial-key messaging with upgrade path
- Docs: added "Choosing a Path" decision table
- README: rewrote hero, moved Quick Start above Security Controls, added
  Hosted vs Self-Hosted comparison table
- Version bumped to 1.5.3

---

## [1.5.2] — 2026-04-07

### Security
- Production startup guard: refuses to start in shadow mode when
  ENVIRONMENT=production (prevents accidental DENIED→PROCEED pass-through)
- Client-side AbortController timeout (8 s) on all demo fetch calls
- Input sanitization: control characters stripped via `sanitizeForDisplay()`
  before rendering receipt values (XSS defense-in-depth)
- Spam-click protection: `useRef` inflight guard prevents duplicate concurrent
  requests regardless of React render batching
- Rate-limit feedback: 429 responses parsed client-side with Retry-After
  countdown shown in the UI

### Added
- `DemoErrorBoundary` component — catches render crashes and shows
  user-friendly fallback with refresh button
- `Retry-After: 5` header on backend 429 responses; demo proxy forwards it
- Demo proxy forwards 429 status from upstream with correct error code
  instead of mapping to generic 503

### Changed
- Error display upgraded: distinct messages for rate-limit, timeout, and
  generic failures (was single "request_failed" for all)
- Version bumped to 1.5.2

---

## [1.5.1] — 2026-04-07

### Security
- Tightened `action` field regex — removed `:` and `.` from allowed characters
  to prevent namespace-injection patterns
- Added Content-Length guard (50 KB limit) to demo proxy route — returns 413
  before parsing oversized payloads

### Changed
- Hosted API status updated from "launching" to "live"
- Version bumped to 1.5.1

---

## [1.5.0] — 2026-04-07

### Security (red team remediation)
- CRITICAL: UpstashRateLimiter now fails closed on Redis error — returns
  False instead of True; circuit breaker opens after 5 consecutive failures
  and resets after 30 seconds
- CRITICAL: _get_client_ip() now validates X-Forwarded-For against
  ALETHEIA_TRUSTED_PROXY_DEPTH (default 1) — prevents IP spoofing via
  injected XFF headers
- CRITICAL: Active mode now refuses to start when ALETHEIA_API_KEYS is
  unset — prevents unauthenticated production deployments
- HIGH: Veto reasons sanitised before client response — similarity scores,
  matched alias phrases, and keyword counts no longer returned to callers
- HIGH: CORS middleware added with ALETHEIA_CORS_ORIGINS allowlist
- HIGH: Demo proxy validates ALETHEIA_BACKEND_URL against allowed host
  suffixes — SSRF guard
- HIGH: Scout _query_history protected by threading.Lock — race condition
  under concurrent workers resolved
- MEDIUM: Sandbox normalises Unicode whitespace before pattern matching —
  thin-space and zero-width character bypass closed
- MEDIUM: print() removed from all agent hot paths — replaced with
  structured logging (aletheia.scout, aletheia.nitpicker, aletheia.judge)

### Added
- ALETHEIA_TRUSTED_PROXY_DEPTH env var (default: 1)
- ALETHEIA_CORS_ORIGINS env var
- tests/test_security_hardening_v2.py — 24 new security tests

### Changed
- Version bumped to 1.5.0

## [1.4.7] — 2026-04-06

### Added
- Upstash Redis distributed rate limiter — sliding window via sorted set,
  survives restarts, synchronizes across workers
- Automatic backend selection: Redis when configured, in-memory fallback
- Startup log clearly indicates which backend is active
- UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN documented in README
  and render.yaml

### Changed
- rate_limiter.allow() is now async in both backends
- In-memory fallback uses asyncio.Lock (was threading.Lock)

## [1.4.4] — 2026-04-06

### Security
- Fix `NameError` in `secure_audit()`: `time.time()` was called but `time` was imported as `_time` — caused every `/v1/audit` request to return 500
- Fix `ImportError` in `/health`: imported `verify_manifest` which does not exist; corrected to `verify_manifest_signature`
- API key comparison now uses `secrets.compare_digest` (constant-time) — previously `not in` set was vulnerable to timing oracle attacks
- Enforce minimum `ALETHEIA_RECEIPT_SECRET` length of 32 characters at startup in active mode — short secrets are rejected before the service accepts traffic
- Rate limiter now caps tracked-IP dictionary at 50,000 entries (LRU eviction) — previously unbounded, allowing memory exhaustion via unique-IP flood

### Fixed
- `main.py` CLI printed stale version string `v1.2.2` — corrected to `v1.4.4`
- `SECURITY.md` referred to project as "Aletheia Cyber-Defense" — corrected to "Aletheia Core"
- `SECURITY.md` contact email updated to `info@aletheia-core.com`
- README: removed false claim that Redis is available for distributed rate limiting — no Redis code exists or has ever existed in this codebase
- README: removed `ALETHEIA_REDIS_URL` from env vars table (was listed as if it did something)
- README: removed `ALETHEIA_REDIS_URL` from the Production Launch Command example
- README: added `GET /health` response schema to API Reference
- README: Security Guarantee row 9 now accurately describes in-memory-only rate limiting
- README: Known Limitations updated to clarify no Redis integration exists
- README: Production support email corrected to `info@aletheia-core.com`

### Added
- `.dockerignore` — prevents private key, test files, and development artifacts from being copied into Docker images
- README: `## Deployment Checklist`, `## Architecture Decision Records`, `## Performance Characteristics` sections

### Changed
- Version bumped to `1.4.4`

---

## [1.4.3] — 2026-04-05

### Security (red team round 2)
- Removed `shadow_verdict` from all client responses — previously logged internally only, but the client response dict could include it under certain code paths
- `_discretise_threat()` discretises raw threat score to band string before any response — raw floats never returned to clients
- Scout `_query_history` capped at 10,000 entries with LRU eviction — prevents memory exhaustion via unique-IP rotation probing
- Dead `asyncio` imports removed from production code paths
- `print()` calls in hot paths converted to `logging` — prevents stdout leakage in production containers

---

## [1.4.2] — 2026-04-04

### Security (red team round 1)
- Receipt HMAC now signs `payload_sha256 + action + origin + issued_at` — prevents replay attacks where a receipt from a benign request is reused for a malicious one
- `ALETHEIA_RECEIPT_SECRET` validated at startup in active mode — service refuses to start without it (`sys.exit(1)`)
- `_get_client_ip()` reads `X-Forwarded-For` then `request.client.host` — IP never taken from request body
- Global exception handler returns opaque error message in active mode — no stack traces exposed
- `/health` strips version and mode from response — prevents information fingerprinting

---

## [1.4.1] — 2026-04-04

### Fixed
- PyPI package metadata corrections: description, keywords, classifiers, homepage URL
- README version badge and install command aligned with PyPI package name (`aletheia-cyber-core`)
- Stale references to removed fields cleaned from documentation

---

## [1.4.0] — 2026-04-04

### Security (enterprise hardening)
- Remove client-supplied IP from request body — rate limiting now derived from network layer (`X-Forwarded-For` or `request.client.host`)
- Add API key authentication via `X-API-Key` header, gated by `ALETHEIA_API_KEYS` env var
- Replace public-key-as-HMAC with real `ALETHEIA_RECEIPT_SECRET` — receipts are now tamper-evident
- Payload logging now stores `payload_sha256` + `payload_length` only in active mode — no plaintext
- Remove build-time manifest signing from `Dockerfile` and `render.yaml`
- Docker now runs as non-root `appuser`
- `audit.log` added to `.gitignore` and removed from git tracking

### Added
- `GET /health` endpoint — returns version, uptime, manifest signature status. No auth required.
- `AuditRequest.client_ip_claim` optional field for audit/debug purposes (never used for enforcement)
- `action` field now validated with pattern `^[A-Za-z0-9_\-:.]+$`

### Changed
- Version bumped to `1.4.0`

---

## [1.3.0] — 2026-04-04

### Added
- Consciousness Proximity Module (Phases 1–4): spectral monitor, identity anchor, sovereign relay, proximity score
- 84 proximity tests (262 total passing)
- `Dockerfile` and `render.yaml` for one-click deployment
- GitHub Actions CI workflow (Python 3.11 + 3.12)
- Devcontainer for one-click Codespaces demo
- Deploy to Render button in README
- `CHANGELOG.md`, issue templates, PR template

### Fixed
- Release workflow now fires on tags only (not every push to main)
- CI uses lightweight `requirements-ci.txt` to avoid torch install timeouts

---

## [1.2.1] — 2026-03-24

### Added
- Batched signed rate-limiting
- NIST AI RMF 1.0 control mapping
- Startup audit health warnings
- Pinned `requirements-lock.txt`
- 181 tests passing

---

## [1.0.0] — 2026-03-16

### Added
- Ed25519 policy manifests with detached signature verification
- HMAC-signed audit receipts (TMR-style)
- Semantic veto engine: Scout (threat scoring), Nitpicker (semantic blocking), Judge (cosine-sim veto)
- Sandbox isolation (text-pattern pre-dispatch heuristic)
- Structured JSON audit logging
- 95 tests passing
