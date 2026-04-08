# Changelog

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
