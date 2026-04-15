<p align="center">
  <img src="assets/logo.png" alt="Aletheia Core" width="180"/>
</p>

<h1 align="center">Aletheia Core</h1>

<p align="center">
  <strong>Runtime audit and pre-execution block layer for AI agents.</strong><br/>
  Signed policy enforcement, semantic threat detection, tamper-evident audit receipts.
</p>

<p align="center">
  <a href="https://app.aletheia-core.com">Website</a> &middot;
  <a href="https://app.aletheia-core.com/demo">Live Demo</a> &middot;
  <a href="https://aletheia-core.com">Docs</a> &middot;
  <a href="SECURITY.md">Security Policy</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.7.0-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/tests-868%20passing-brightgreen" alt="Tests"/>
  <img src="https://github.com/holeyfield33-art/aletheia-core/actions/workflows/ci.yml/badge.svg" alt="CI" />
</p>

---

## Why Aletheia Core

Autonomous AI agents manage CI/CD pipelines, financial transactions, and critical infrastructure.
A single compromised dependency can silently exfiltrate credentials from production environments.
Existing guardrails operate at the token level — they cannot detect semantically camouflaged
instructions or verify policy integrity at runtime.

Aletheia provides a **runtime enforcement layer** that interposes between AI agents and the
actions they request. Every action is verified against a cryptographically signed policy
manifest, analyzed for semantic similarity to known attack patterns, and logged with a
tamper-evident audit receipt — before it is allowed to execute.

**Key properties:**
- Ed25519-signed policy manifest — tamper triggers hard veto
- Semantic intent veto — cosine similarity against 50+ camouflage phrases
- HMAC-signed audit receipts on every decision
- Fail-closed design — invalid manifest or unverifiable action = automatic DENIED
- MIT open source — read every line that determines an allow or block

---

## What's New in v1.7.0

### Security Debt Burn-Down
- **SSRF hardening**: backend host validation now requires exact host or real subdomain match.
- **Manifest pinning**: startup verifies `ALETHEIA_MANIFEST_HASH` when set and refuses mismatches.
- **Health endpoint hardening**: public `/health` is minimal; detailed diagnostics require `X-Admin-Key`.
- **Tamper-evident audit chain**: each audit record now includes `seq`, `prev_hash`, and `record_hash`.
- **Regex hardening**: removed nested-quantifier ReDoS vector and bounded high-risk sandbox patterns.
- **Secret guardrails**: production `NEXTAUTH_SECRET` requires 32+ characters at runtime.

### Product Surface Expansion
- **Theme toggle**: persistent dark/light mode across sessions.
- **New docs surfaces**: `/changelog` and `/cli` pages.
- **Engineering blog**: `/blog` index plus static post pages with metadata, robots, and sitemap entries.
- **Navigation/footer updates**: user-facing links now include Blog, Changelog, and CLI.
- **Dependency cleanup**: removed dead Supabase utility code from app runtime.

See [CHANGELOG.md](CHANGELOG.md) for full history.

---

## Security Status

| Metric | Value |
|--------|-------|
| Audit status | **PASS** |
| Tests passing | 698 |
| Core coverage | 89% |
| SAST findings | 0 |
| Hardcoded secrets | 0 |
| Dependency hash pinning | Enforced (`--require-hashes` in Dockerfile) |

---

## Quick Start

### Try the live demo (no install)

[**app.aletheia-core.com/demo**](https://app.aletheia-core.com/demo) — no API key required.

### Install

```bash
pip install aletheia-cyber-core
```

#### Optional Consciousness Proximity Module

To enable the optional proximity feature set:

```bash
pip install -r requirements-proximity.txt
export CONSCIOUSNESS_PROXIMITY_ENABLED=true
```

The proximity module is gated behind `CONSCIOUSNESS_PROXIMITY_ENABLED=true` and includes optional runtime dependencies for governance monitoring and relay scoring.

### Sign the manifest (required before first run)

```bash
python main.py sign-manifest
```

### Run a local audit

```bash
python main.py
```

### Start the API server

```bash
uvicorn bridge.fastapi_wrapper:app --host 0.0.0.0 --port 8000
```

### Run the test suite

```bash
pytest tests/ -v --ignore=tests/test_api.py
```

---

## Architecture

Aletheia operates via a tri-agent consensus model:

```
Incoming Request
│
├─ Input Hardening (NFKC, Base64, URL decode)
│
▼
┌─────────────────┐
│      Scout      │  Threat intelligence, swarm detection, IP scoring
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Nitpicker    │  Polymorphic intent analysis, lineage tracing,
│                 │  semantic blocked-pattern detection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      Judge      │  Manifest signature verification, policy veto,
│                 │  semantic alias veto, grey-zone escalation,
│                 │  action sandbox check
└────────┬────────┘
         │
    PROCEED / DENY
         │
         ▼
   Audit Log + TMR Receipt
```

---

## API Reference

**POST** `/v1/audit`

Request:

```json
{
  "payload": "string (max 10,000 chars)",
  "origin": "string (max 128 chars)",
  "action": "string — pattern: ^[A-Za-z0-9_\\-:.]+$",
  "client_ip_claim": "string (optional, audit/debug only — never used for enforcement)"
}
```

Response:

```json
{
  "decision": "PROCEED | DENIED | RATE_LIMITED | SANDBOX_BLOCKED",
  "metadata": {
    "threat_level": "LOW | MEDIUM | HIGH | CRITICAL",
    "latency_ms": 14.0,
    "request_id": "a1b2c3d4e5f6g7h8",
    "client_id": "ALETHEIA_ENTERPRISE"
  },
  "receipt": {
    "decision": "PROCEED",
    "policy_hash": "sha256...",
    "payload_sha256": "sha256...",
    "action": "Read_Report",
    "origin": "trusted_admin",
    "signature": "hmac-sha256...",
    "issued_at": "ISO-8601"
  }
}
```

**Note:** `shadow_verdict` and `redacted_payload` are never returned to clients. `client_ip_claim`, if provided, is stored in the audit log for debugging only and is never used for enforcement.

---

**GET** `/health`

No auth required for the baseline probe. Detailed diagnostics require `X-Admin-Key`.

```json
{
  "status": "ok",
  "service": "aletheia-core"
}
```

With valid `X-Admin-Key`, `/health` additionally returns:
`version`, `uptime_seconds`, `timestamp`, and `manifest_signature`.

---

**GET** `/ready`

No auth required. Returns HTTP 200 when all subsystems are healthy, HTTP 503 when degraded.

```json
{
  "ready": true,
  "manifest_signature": "VALID",
  "policy_version": "1.0",
  "receipt_signing_configured": true
}
```

When `ready` is `false`, privileged actions are denied (fail-closed). Read-only actions continue.

---

**GET** `/metrics`

No auth required. Returns Prometheus/OpenMetrics-format metrics for scraping.

Exported metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `aletheia_requests_total` | Counter | Total audit requests, labeled by `agent` and `verdict` |
| `aletheia_latency_seconds` | Histogram | Request processing latency |
| `aletheia_embedding_model_load_seconds` | Gauge | Time to load the embedding model at startup |
| `aletheia_keys_total` | Gauge | Number of active API keys |
| `aletheia_audit_log_bytes` | Counter | Total bytes written to the audit log |

---

**POST** `/v1/rotate`

Admin-only. Requires `X-Admin-Key` header matching `ALETHEIA_ADMIN_KEY`. Hot-rotates secrets without restart.

On rotation, reloads: `ALETHEIA_RECEIPT_SECRET`, `ALETHEIA_API_KEYS`, `ALETHEIA_ALIAS_SALT`, `ALETHEIA_ADMIN_KEY`. Re-verifies the manifest signature and rotates the Judge alias bank.

**Cooldown:** 10 seconds between rotations. Returns HTTP 429 with `retry_after_seconds` if called too soon.

**Rotation via signal:** `kill -SIGUSR1 $(pidof python)` performs the same rotation without an HTTP call.

```bash
curl -X POST http://localhost:8000/v1/rotate \
  -H "X-Admin-Key: $ALETHEIA_ADMIN_KEY"
```

---

**Key Management Endpoints** (all require `X-Admin-Key` header):

| Method | Path | Description |
|--------|------|-------------|
| `POST /v1/keys` | Create a new API key (trial or pro plan). Returns raw key once. |
| `GET /v1/keys` | List all keys (metadata only, no raw keys or hashes). |
| `DELETE /v1/keys/{id}` | Revoke a key by ID. |
| `GET /v1/keys/{id}/usage` | Get usage statistics for a key. |

---

## Project Structure

```
aletheia-cyber-core/
├── agents/
│   ├── scout_v2.py          # Threat intelligence + swarm detection
│   ├── nitpicker_v2.py      # Polymorphic intent sanitization + embeddings
│   └── judge_v1.py          # Policy enforcement + semantic veto
├── bridge/
│   ├── fastapi_wrapper.py   # Production REST API (rate-limited, audited)
│   ├── config.py            # Legacy config shim
│   └── utils.py             # Input hardening (homoglyphs, Base64, URL)
├── core/
│   ├── config.py            # Centralized settings (env / yaml / defaults)
│   ├── embeddings.py        # Shared SentenceTransformer service
│   ├── audit.py             # Structured JSON logging + TMR receipts + PII redaction
│   ├── rate_limit.py        # Sliding-window rate limiter (Upstash Redis / in-memory)
│   ├── sandbox.py           # Action sandbox pattern scanner
│   ├── runtime_security.py  # Input normalization + semantic intent classification
│   ├── key_store.py         # SQLite-backed API key store with quota enforcement
│   ├── decision_store.py    # Decision replay defense store
│   ├── metrics.py           # Prometheus metrics definitions
│   └── secret_rotation.py   # Hot secret rotation (SIGUSR1 + /v1/rotate)
├── manifest/
│   ├── security_policy.json        # Ground truth veto rules
│   ├── security_policy.json.sig    # Ed25519 detached signature
│   ├── security_policy.ed25519.pub # Public verification key
│   └── signing.py           # Manifest signing and verification
├── deploy/
│   └── logrotate.conf       # Log rotation config for container deployments
├── scripts/
│   ├── backup_sqlite.sh     # SQLite backup with 7-day retention
│   └── smoke_test_live.py   # Post-deploy smoke tests
├── tests/                   # 697 tests across core, agents, security, and API modules
├── simulations/             # Adversarial simulation scripts
├── main.py                  # CLI entry point
├── AGENTS.md                # Agent communication protocol
├── Dockerfile               # Production container with HEALTHCHECK, non-root user
└── requirements.txt         # Hash-pinned dependencies
```

---

## Hosted vs Self-Hosted

| | **Self-Hosted (Community)** | **Hosted Trial** | **Hosted Pro** |
|---|---|---|---|
| **Price** | Free (MIT) | Free | $49/mo |
| **Hosting** | You manage | Managed | Managed |
| **API keys** | You configure | One trial key | Production keys |
| **Audit logs** | Your storage | None | 30-day retention |
| **Support** | GitHub community | — | Priority support |
| **Use case** | Full control, research | Evaluation | Production |

- **Live demo** — free, no API key required: [app.aletheia-core.com/demo](https://app.aletheia-core.com/demo)
- **Self-hosted** — the open-source engine. Clone the repo, sign a manifest, run the server.
- **Hosted Trial** — free evaluation key with limited monthly requests.
- **Hosted Pro** — production API access, managed infrastructure, retained audit logs.
- **Services** — starting at $2,500 for red-team review, custom policy engineering, deployment guidance.

---

## Production Usage

### Configuration

All settings are configurable via environment variables (prefixed `ALETHEIA_`) or `config.yaml`:

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `intent_threshold` | `ALETHEIA_INTENT_THRESHOLD` | `0.55` | Cosine similarity threshold for semantic veto |
| `grey_zone_lower` | `ALETHEIA_GREY_ZONE_LOWER` | `0.40` | Lower bound of the grey-zone escalation band |
| `rate_limit_per_second` | `ALETHEIA_RATE_LIMIT_PER_SECOND` | `10` | Max requests per second per IP |
| `mode` | `ALETHEIA_MODE` | `active` | Defense mode: `active`, `shadow`, or `monitor` |
| `log_level` | `ALETHEIA_LOG_LEVEL` | `INFO` | Logging verbosity |
| `audit_log_path` | `ALETHEIA_AUDIT_LOG_PATH` | `audit.log` | Path to the structured audit log |

### Known Limitations

- **Rate limiting:** When `UPSTASH_REDIS_REST_URL` is configured, rate limiting
  is distributed across all workers and instances via Upstash Redis (sliding window,
  sorted set per IP). Without Upstash credentials, falls back to an in-memory
  limiter that resets on restart and does not synchronize across workers.
  Set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` for production
  deployments behind multiple workers.
- **Embedding model requires ~500 MB on disk.** The `all-MiniLM-L6-v2` model is downloaded on first use. Pre-pull in your Docker image build step.
- **Static alias bank.** While daily rotation mitigates probing, a determined adversary with prolonged access could enumerate patterns. Consider supplementing with an LLM-based classifier for high-sensitivity deployments.
- **No runtime syscall interception.** The action sandbox validates declared intents, not runtime behavior. Pair with OS-level sandboxing (seccomp, AppArmor) for defense in depth.

### Security Assumptions

Aletheia is a **runtime enforcement layer**. It validates declared intents and policy compliance — it does not sandbox process execution at the OS level. For defense-in-depth, pair with OS-level sandboxing (AppArmor, seccomp-bpf) and network-level controls.

| Assumption | Implication |
|---|---|
| Aletheia sees all agent actions | Deploy as an inline proxy or SDK wrapper, not a sidecar that can be bypassed |
| Policy manifest is signed offline | The Ed25519 private key must never reside on the runtime host |
| HMAC receipts prove decision integrity | They do not prove the action was actually executed — pair with execution logs |
| Embeddings are deterministic per model version | Model upgrades may shift similarity scores; re-validate thresholds after upgrades |

### NIST AI RMF Alignment

Aletheia maps to the [NIST AI Risk Management Framework](https://www.nist.gov/artificial-intelligence/risk-management-framework) core functions:

| NIST Function | Aletheia Mechanism |
|---|---|
| **GOVERN** | Ed25519-signed policy manifests enforce organisational risk tolerance as immutable, versioned artefacts |
| **MAP** | Semantic intent classifier categorises each request into one of 5 risk categories before agent evaluation |
| **MEASURE** | HMAC-signed audit receipts provide cryptographically verifiable evidence of every enforcement decision |
| **MANAGE** | Daily alias rotation, configurable thresholds, and `active`/`shadow`/`monitor` modes enable adaptive risk response |

---

## Security Controls

The following controls are implemented and tested in the current codebase:

| Control | Implementation | Verified by |
|---------|---------------|-------------|
| Ed25519 manifest signing | `manifest/signing.py` — detached signature verified before every policy load. Tamper or missing signature = hard veto. | `test_judge_manifest.py` |
| Semantic intent veto | `agents/judge_v1.py` — cosine similarity against 50+ camouflage aliases across 6 restricted action categories. Two-tier veto: primary threshold (0.55) and grey-zone band (0.40–0.55) with keyword heuristics. | `test_judge.py`, `test_hardening.py` |
| HMAC-signed audit receipts | `core/audit.py` — every decision produces an HMAC-SHA256 receipt binding decision, policy hash, payload SHA-256, action, and origin. | `test_enterprise.py` |
| PII redaction | `core/audit.py` — email, phone, SSN, and credit card patterns replaced with `[REDACTED:<type>:<hash>]` before writing to audit logs. Controlled by `ALETHEIA_LOG_PII`. | `test_pii_redaction.py` |
| Config ownership enforcement | `core/config.py` — rejects config files writable by non-owners on shared hosts. | `test_config_ownership.py` |
| Secret rotation | `core/secret_rotation.py` — hot-rotate secrets via `POST /v1/rotate` (admin-only, 10s cooldown) or `kill -SIGUSR1`. | `test_core.py` |
| Input hardening | `bridge/utils.py` — NFKC normalization, zero-width character strip, recursive Base64 decode (up to 5 layers with 10× size bomb protection), URL percent-encoding decode. | `test_hardening.py` |
| Action sandbox | `core/sandbox.py` — regex-based pattern scanner blocks subprocess, socket, eval, filesystem destruction, and privilege escalation patterns. Unicode whitespace normalized before matching. | `test_hardening.py` |
| Rate limiting | `core/rate_limit.py` — sliding-window per-IP rate limiting. Upstash Redis backend or in-memory fallback. 50,000 IP cap with LRU eviction. Circuit breaker with jitter on recovery. | `test_rate_limit_extended.py` |
| Timing-safe auth | `bridge/fastapi_wrapper.py` — `secrets.compare_digest` for all key comparisons; all keys evaluated before returning. | `test_hardening.py` |
| Proxy depth validation | `bridge/fastapi_wrapper.py` — `ALETHEIA_TRUSTED_PROXY_DEPTH` validated to 0–5 range; XFF ignored when depth=0. | `test_security_hardening_v2.py` |
| Security headers | FastAPI middleware and `vercel.json` — CSP, Permissions-Policy, X-Frame-Options, X-Content-Type-Options, Cache-Control. | `test_hardening.py` |
| ReDoS protection | Sandbox patterns use word boundaries and fixed anchors; regex input length bounded by Pydantic `max_length` validators. | `test_hardening.py` |
| Container hardening | `Dockerfile` — non-root user, `HEALTHCHECK`, `--timeout-keep-alive`, restrictive `/app/data` permissions, `--require-hashes` for dependency pinning. | Manual verification |

---

## Limitations / Not Yet Implemented

- **No OS-level sandboxing.** Aletheia validates declared intents, not runtime behavior. It does not intercept syscalls. Pair with seccomp, AppArmor, or gVisor for defense in depth.
- **No LLM-based classifier.** Semantic veto uses a static embedding model (`all-MiniLM-L6-v2`). A determined adversary with prolonged access could enumerate alias patterns. An LLM-based classifier is not yet implemented.
- **No webhook / event streaming.** Audit decisions are logged to a local file. There is no built-in webhook, Kafka, or event-streaming integration.
- **No multi-tenant isolation.** The key store supports trial/pro plans with quotas, but there is no tenant-level data isolation or per-tenant policy manifests.
- **No live streaming log tail.** The dashboard now includes a paginated audit logs viewer, but it does not yet support real-time stream subscriptions.
- **Single embedding model.** Only `all-MiniLM-L6-v2` is supported. Model selection is not yet configurable at runtime.
- **In-memory rate limiter resets on restart** unless Upstash Redis is configured. SQLite fallback for the decision store does not synchronize across workers.

---

## Support

If this project is useful to your organization, consider reaching out about our [managed services and enterprise plans](mailto:info@aletheia-core.com).

---

## Environment Variables

Comprehensive local + hosted configuration is documented in:
**[docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md)**

Below is the quick-start subset.

| Variable | Required | Description |
|---|---|---|
| `ALETHEIA_API_KEYS` | Production | Comma-separated API keys for `X-API-Key` auth. Unset = open mode. |
| `ALETHEIA_RECEIPT_SECRET` | YES (production) | HMAC secret for audit receipts. Service will NOT boot in active mode without this. Min 32 chars. Generate via `openssl rand -hex 32`. |
| `ALETHEIA_ADMIN_KEY` | Production | Admin key for `/v1/keys` and `/v1/rotate` endpoints. Constant-time compared. |
| `ALETHEIA_ALIAS_SALT` | RECOMMENDED | Salt for daily alias rotation. Prevents enumeration attacks. Generate via `openssl rand -hex 32`. |
| `ALETHEIA_KEY_SALT` | RECOMMENDED | HMAC salt for key store hashing. Falls back to plain SHA-256 with a logged warning if unset. |
| `ALETHEIA_MODE` | No | `active` (default), `shadow`, or `monitor`. Production refuses to start in shadow mode when `ENVIRONMENT=production`. |
| `ALETHEIA_LOG_LEVEL` | No | `INFO` (default), `DEBUG`, `WARNING` |
| `ALETHEIA_AUDIT_LOG_PATH` | No | Path to the structured audit log. Default: `audit.log`. Rejects `..` path components. |
| `ALETHEIA_RATE_LIMIT_PER_SECOND` | No | Requests per IP per second. Default: `10` |
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | No | Number of trusted reverse proxies (0–5). Default: `1`. Set to `0` for direct connections. |
| `ALETHEIA_CORS_ORIGINS` | No | Comma-separated allowed CORS origins. Default: `https://app.aletheia-core.com,https://aletheia-core.com` |
| `ALETHEIA_CONFIG_PATH` | No | Path to a YAML config file. Default: searches for `config.yaml` / `config.yml` in the working directory. |
| `ALETHEIA_KEYSTORE_PATH` | No | Path to the key store SQLite database. |
| `ALETHEIA_MANIFEST_KEY_VERSION` | No | Key version tag for manifest signing. Default: `v1`. |
| `ALETHEIA_LOG_PII` | No | Set to `true` to disable PII redaction in audit logs. Default: `false` (PII is redacted). |
| `UPSTASH_REDIS_REST_URL` | Recommended | Upstash Redis REST endpoint for distributed rate limiting. Falls back to in-memory if absent. |
| `UPSTASH_REDIS_REST_TOKEN` | Recommended | Upstash Redis REST token. Required when URL is set. |
| `CONSCIOUSNESS_PROXIMITY_ENABLED` | No | Enable optional proximity module. Default: `false`. |
| `ENVIRONMENT` | No | Set to `production` to enforce active mode and require `ALETHEIA_API_KEYS`. |
| `ALETHEIA_DB_PATH` | No | Path to the SQLite decision store. Default: `data/aletheia_decisions.sqlite3`. Used by backup script. |
| `ALETHEIA_BACKUP_RETENTION_DAYS` | No | Days to retain SQLite backups. Default: `7`. Used by `scripts/backup_sqlite.sh`. |

---

## Pre-Launch Verification

Before starting the service in production, complete the following checklist:

### 1. Verify required secrets are set

```bash
# ALETHEIA_RECEIPT_SECRET is mandatory for active mode
if [ -z "$ALETHEIA_RECEIPT_SECRET" ]; then
  echo "ERROR: ALETHEIA_RECEIPT_SECRET not set"
  exit 1
fi

# ALETHEIA_ALIAS_SALT is recommended
if [ -z "$ALETHEIA_ALIAS_SALT" ]; then
  echo "WARNING: ALETHEIA_ALIAS_SALT not set — alias rotation is predictable"
fi

# ALETHEIA_API_KEYS must be set in active mode
if [ -z "$ALETHEIA_API_KEYS" ]; then
  echo "ERROR: ALETHEIA_API_KEYS not set — service will refuse to start in active mode"
  exit 1
fi
echo "ALETHEIA_API_KEYS length: ${#ALETHEIA_API_KEYS}"
```

### 2. Test the health endpoint

```bash
curl http://localhost:8000/health
# Expected unauthenticated response:
# {
#   "status": "ok",
#   "service": "aletheia-core"
# }
```

### 3. Verify receipt signing works

```bash
curl -X POST http://localhost:8000/v1/audit \
  -H "Content-Type: application/json" \
  -d '{
    "payload": "test payload",
    "origin": "admin",
    "action": "Read_Report"
  }'
# Response must include "signature" field with non-empty HMAC-SHA256 hex string
# DO NOT use UNSIGNED_DEV_MODE in production
```

### 4. Confirm shadow mode does not leak verdicts

```bash
ALETHEIA_MODE=shadow uvicorn bridge.fastapi_wrapper:app --port 8000 &
sleep 2

curl -X POST http://localhost:8000/v1/audit \
  -H "Content-Type: application/json" \
  -d '{"payload": "transfer funds", "origin": "user", "action": "Transfer_Funds"}'
# Response MUST NOT contain "shadow_verdict" field (even though action is blocked internally)
```

### Production Launch Command

```bash
# Generate secure secrets
ALETHEIA_RECEIPT_SECRET=$(openssl rand -hex 32)
ALETHEIA_ALIAS_SALT=$(openssl rand -hex 32)

# Start in active mode
ALETHEIA_MODE=active \
ALETHEIA_RECEIPT_SECRET="$ALETHEIA_RECEIPT_SECRET" \
ALETHEIA_ALIAS_SALT="$ALETHEIA_ALIAS_SALT" \
uvicorn bridge.fastapi_wrapper:app --host 0.0.0.0 --port 8000
```

---

## Deployment Checklist

Before going live in `active` mode, verify all of the following:

| # | Check | Command |
|---|-------|---------|
| 1 | Manifest is signed | `python main.py sign-manifest` |
| 2 | `ALETHEIA_RECEIPT_SECRET` is set (≥ 32 chars) | `echo ${#ALETHEIA_RECEIPT_SECRET}` |
| 3 | `ALETHEIA_ALIAS_SALT` is set | `echo ${#ALETHEIA_ALIAS_SALT}` |
| 4 | Health endpoint returns `"status":"ok"` | `curl http://localhost:8000/health` |
| 5 | Receipt signature is not `UNSIGNED_DEV_MODE` | Inspect `signature` field in `/v1/audit` response |
| 6 | Tests pass | `pytest tests/ --ignore=tests/test_api.py -q` |
| 7 | Private key is NOT in Docker image | `docker run --rm <image> ls /app/manifest/*.key` — must error |

Required environment variables:

| Variable | Required | Min Length | Notes |
|---|---|---|---|
| `ALETHEIA_RECEIPT_SECRET` | YES (active mode) | 32 chars | Generate: `openssl rand -hex 32` |
| `ALETHEIA_ALIAS_SALT` | RECOMMENDED | 32 chars | Generate: `openssl rand -hex 32` |
| `ALETHEIA_API_KEYS` | RECOMMENDED | — | Comma-separated. Unset = open mode. |
| `ALETHEIA_MODE` | No | — | `active` (default), `shadow`, `monitor` |
| `ALETHEIA_RATE_LIMIT_PER_SECOND` | No | — | Default: `10` |
| `ALETHEIA_LOG_LEVEL` | No | — | Default: `INFO` |
| `ALETHEIA_AUDIT_LOG_PATH` | No | — | Default: `audit.log` |

---

## Architecture Decision Records

**ADR-001: Two-tier rate limiting**
Rate limiting supports two backends. When `UPSTASH_REDIS_REST_URL` is configured, rate limiting uses Upstash Redis (sliding-window sorted set per IP), synchronizing across workers and surviving restarts. Without Redis, it falls back to an in-memory limiter that resets on restart and does not synchronize across workers. For horizontal scaling without Upstash, place a rate-limiting proxy (nginx, Cloudflare, Traefik) in front.

**ADR-002: Threat score discretisation**
Raw cosine-similarity floats and threat scores are never returned to clients. Returning exact values would let an attacker black-box calibrate their payload against the exact veto threshold. Only discretised bands (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`) are exposed.

**ADR-003: Startup rejection without RECEIPT_SECRET**
The service `sys.exit(1)` in `active` mode without `ALETHEIA_RECEIPT_SECRET`. An unsigned receipt (`UNSIGNED_DEV_MODE`) in production would allow an attacker to forge receipts, breaking audit trail integrity. Hard refusal is preferable to degraded operation.

**ADR-004: Ed25519 for manifest signing**
Ed25519 was chosen over RSA for manifest signing: smaller keys, faster verification, no padding oracle attacks, and deterministic signatures. The public key ships with the package; the private key never leaves the operator's control.

---

## Performance Characteristics

Measured on a 2-core VM with the `all-MiniLM-L6-v2` model pre-warmed:

| Metric | Value | Notes |
|--------|-------|-------|
| Cold-start (model load) | ~3–8 s | Model downloaded on first use if not cached |
| Warm-start (subsequent requests) | ~12–40 ms p99 | Embedding encode dominates |
| Sandbox check only | < 1 ms | Pure regex, no model |
| Memory footprint | ~500 MB | Dominated by PyTorch + model weights |
| Rate limit overhead | < 0.1 ms | In-memory list operations with threading.Lock |

The embedding model is loaded eagerly at startup (`warm_up()`) to eliminate cold-start latency on the first production request.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues and pull requests.

## Security

See [SECURITY.md](SECURITY.md) for responsible disclosure policy.

**What Aletheia is:**
- Runtime enforcement layer — gates agent actions before execution
- Signed audit evidence — tamper-evident receipts on every decision
- One layer in a broader security stack — designed for auditability

**What it is not:**
- Not a replacement for model alignment
- Not an OS-level sandbox — validates declared intents, not runtime behavior
- Not a compliance certification — consult qualified counsel

## License

[MIT](LICENSE) — Copyright (c) 2026 Ashura Joseph Holeyfield — Aletheia Sovereign Systems
