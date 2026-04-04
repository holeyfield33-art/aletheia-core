# Changelog

All notable changes are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
