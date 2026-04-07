<p align="center">
  <img src="assets/logo.png" alt="Aletheia Core" width="180"/>
</p>

<h1 align="center">Aletheia Core</h1>

<p align="center">
  <strong>Enterprise-Grade System 2 Security for AI Agents</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.6.0-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/tests-548%20passing-brightgreen" alt="Tests"/>
  <img src="https://img.shields.io/badge/security-audited-brightgreen" alt="Security Audit"/>
  <img src="https://img.shields.io/badge/status-production--ready-brightgreen" alt="Status"/>
  <img src="https://github.com/holeyfield33-art/aletheia-core/actions/workflows/ci.yml/badge.svg" alt="CI" />
  <a href="https://render.com/deploy?repo=https://github.com/holeyfield33-art/aletheia-core">
    <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render" height="28" />
  </a>
</p>

<p align="center">
  <a href="docs/index.html">📖 Documentation</a> •
  <a href="https://github.com/holeyfield33-art/aletheia-core">GitHub</a> •
  <a href="https://codespaces.new/holeyfield33-art/aletheia-core">
    <img src="https://github.com/codespaces/badge.svg" alt="Open in GitHub Codespaces" />
  </a>
</p>

---

## The Problem

Autonomous AI agents increasingly manage CI/CD pipelines, financial transactions, and
critical infrastructure. The [LiteLLM supply-chain attack](https://github.com/BerriAI/litellm)
demonstrated that a single compromised dependency can silently exfiltrate credentials from
thousands of production environments. Existing guardrails operate at the token level —
they cannot detect semantically camouflaged instructions or verify policy integrity
at runtime.

Aletheia provides a **System 2 reasoning layer** that interposes between AI agents and
the actions they request. Every action is verified against a cryptographically signed
policy manifest, analyzed for semantic similarity to known attack patterns, and logged
with a tamper-evident audit receipt — before it is allowed to execute.

---

## Security Guarantees

The following properties are cryptographically or architecturally enforced:

| # | Guarantee | Mechanism |
|---|-----------|-----------|
| 1 | **Tamper-proof policy manifest** | Ed25519 detached signature verified before every policy load. Invalid or missing signature causes a hard crash (`ManifestTamperedError`). |
| 2 | **Semantic intent veto** | SentenceTransformer (`all-MiniLM-L6-v2`) cosine similarity against 50+ camouflage phrases. Configurable threshold (default 0.55). |
| 3 | **Grey-zone escalation** | Payloads in the ambiguous similarity band (0.40–0.55) are second-pass classified via keyword heuristics. Two or more high-risk keyword hits trigger a veto. |
| 4 | **Action sandbox** | Regex-based pattern scanner blocks subprocess exec, raw socket, `eval`, filesystem destruction, and privilege-escalation patterns before dispatch. |
| 5 | **Daily alias rotation** | Semantic alias phrase order is deterministically shuffled daily (HMAC-SHA256 seed from date + manifest hash + `ALETHEIA_ALIAS_SALT`) to prevent reverse-engineering via probing. |
| 6 | **Embedding pre-warming** | Model loaded eagerly at FastAPI startup to eliminate cold-start latency on the first request. |
| 7 | **Audit trail integrity** | Every decision produces a structured JSON log line and an HMAC-signed TMR receipt (decision + policy hash + payload_sha256 + action + origin + signature). |
| 8 | **Input hardening** | NFKC homoglyph collapse, zero-width character strip, bounded URL percent-encoding decode (depth 5, budget 24), bounded Base64 decode with size-bomb protection, JSON/hex unescape, entropy quarantine, and strict Pydantic schema validation — all applied before any agent sees the payload. |
| 9 | **Rate limiting** | Sliding-window per-IP rate limiter. Distributed via Upstash Redis when `UPSTASH_REDIS_REST_URL` is configured (survives restarts, synchronizes across workers). Falls back to in-memory for single-node deployments. |
| 10 | **No stack-trace leakage** | Global FastAPI exception handler returns an opaque error in production mode. Version and mode never exposed to unauthenticated /health callers. |
| 11 | **Config-driven defense modes** | `active` / `shadow` / `monitor` — switchable via environment variable or `config.yaml` without code changes. |
| 12 | **Receipt replay resistance** | HMAC signature includes payload_sha256, action, origin, request_id, policy_version, manifest_hash, fallback_state, and decision_token. Receipts are bound to a unique request and rejected on replay. |
| 13 | **Semantic intent classification** | Five-category blocked-intent classifier (malicious_capability, data_exfiltration, privilege_escalation, tool_abuse, policy_evasion) with coercive pattern detection and fail-closed uncertain confidence. Catches paraphrases, euphemisms, and roleplay-based bypass attempts. |
| 14 | **Distributed replay defense** | SHA256 decision tokens bound to request_id, timestamp, policy_version, and manifest_hash. NX-based idempotent claims with SQLite local fallback and optional Upstash Redis centralized store. |
| 15 | **Fail-closed degraded mode** | Privileged actions are denied when remote dependencies are unavailable. Only explicitly safe read-only paths are allowed in degraded mode. Fallback state is recorded in every receipt. |
| 16 | **Manifest version and expiry** | Manifest metadata includes `version`, `expires_at`, and `key_version`. Stale, expired, or version-mismatched manifests are hard-rejected at startup. |
| 17 | **Deployment drift detection** | Workers verify they use the same signed policy bundle. Mismatched manifest hash or policy version across instances triggers a hard deny. |

Additional guarantees:

- **API Key Authentication** — `X-API-Key` header required when `ALETHEIA_API_KEYS` is configured
- **Real Client IP** — rate limiting derived from network layer, never from request body
- **Payload Privacy** — audit logs store SHA-256 hash + length only; no plaintext content in active mode
- **Receipt Signing** — HMAC receipts use `ALETHEIA_RECEIPT_SECRET`; must be set for active mode
- **Shadow Verdict Blocking** — In shadow mode, blocks are logged but not exposed to clients

---

## Key Features

- **Cryptographic Policy Integrity** — Ed25519-signed security manifest with version, expiry, and key rotation metadata; tamper triggers an instant hard veto
- **Semantic Intent Analysis** — Cosine similarity replaces string matching; catches camouflaged fund transfers, privilege escalation, and data exfiltration
- **Semantic Intent Classification** — Five-category blocked-intent classifier detects paraphrases, euphemisms, roleplay, and coercive instruction patterns; fails closed when uncertain
- **Grey-Zone Second-Pass Classifier** — Keyword heuristics catch creative paraphrases that fall below the primary threshold
- **Action Sandbox** — Pattern-based scanner blocks subprocess, eval, raw socket, and filesystem-destruction payloads
- **Polymorphic Defense** — Config-driven deterministic rotation across LINEAGE, INTENT, and SKEPTIC modes
- **Structured Audit Trail** — JSON-line logging with HMAC-signed TMR receipts on every decision, bound to request ID, policy version, and manifest hash
- **Rate Limiting** — Sliding-window limiter (10 req/s per IP, configurable) with Upstash Redis for distributed deployments
- **Input Hardening** — Homoglyph normalization, bounded Base64/URL-encoding decode, JSON/hex unescape, entropy quarantine, strict schema validation
- **Distributed Replay Defense** — SHA256 decision tokens with idempotent claims, SQLite local fallback, and deployment drift detection across workers
- **Fail-Closed Degraded Mode** — Privileged actions denied when remote dependencies are unavailable; read-only paths allowed with observable fallback state
- **Daily Alias Rotation** — Alias bank order shuffled deterministically per day to resist probing
- **Swarm-Resistant Triage** — Scout agent clusters diversionary noise and prioritizes high-blast-radius threats

---

## Quick Start

### Install from PyPI

```bash
pip install aletheia-cyber-core
```

### Install from source

```bash
git clone https://github.com/holeyfield33-art/aletheia-core.git
cd aletheia-core
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

#### Optional: Consciousness Proximity Module

```bash
pip install -r requirements-proximity.txt
export CONSCIOUSNESS_PROXIMITY_ENABLED=true
```

#### Optional: Development dependencies (testing)

```bash
pip install -e ".[dev]"
```

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

### Run the live demo

```bash
bash demo.sh
```

### Run the test suite

```bash
# Full test suite (requires torch + sentence-transformers)
pytest tests/ -v

# CI-lightweight (skips embedding-dependent tests)
pytest tests/ -v --ignore=tests/test_api.py
```

---

## Deployment

### Deploy to Render

One-click deploy:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/holeyfield33-art/aletheia-core)

Or manually:
1. Connect your GitHub repo in the Render dashboard.
2. Render reads `render.yaml` automatically — it defines the build, start command, and env vars.
3. Set the following env vars in the Render dashboard:
   - `ALETHEIA_RECEIPT_SECRET` — generate with `openssl rand -hex 32`
   - `ALETHEIA_ALIAS_SALT` — generate with `openssl rand -hex 32`
   - `ALETHEIA_API_KEYS` — comma-separated API keys for authentication
   - `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` — for distributed rate limiting (recommended)
4. Sign the manifest locally (`python main.py sign-manifest`) and commit `security_policy.json.sig` before deploying.
5. Verify after deploy: `curl https://<your-app>.onrender.com/health`

### Deploy to Vercel (frontend dashboard)

The Next.js dashboard is deployed separately from the Python API:

1. Connect the repo in the Vercel dashboard.
2. Vercel reads `vercel.json` — framework is `nextjs`, build command is `npm run build`.
3. Set the `NEXT_PUBLIC_ALETHEIA_API_URL` env var to your Render API URL.
4. Deploy. The frontend calls the API via the `/api/demo` proxy route.

### Deploy with Docker

```bash
# Build
docker build -t aletheia-core .

# Run
docker run -d \
  -p 8000:8000 \
  -e ALETHEIA_MODE=active \
  -e ALETHEIA_RECEIPT_SECRET=$(openssl rand -hex 32) \
  -e ALETHEIA_ALIAS_SALT=$(openssl rand -hex 32) \
  -e ALETHEIA_API_KEYS=your-api-key-here \
  aletheia-core
```

The Dockerfile:
- Uses `python:3.11-slim`
- Verifies the manifest signature exists at build time
- Creates a non-root user (`appuser`) for runtime
- Exposes port 8000
- Starts with `uvicorn bridge.fastapi_wrapper:app`

### Install from PyPI (library use)

```bash
pip install aletheia-cyber-core
```

Use the CLI entry point:

```bash
aletheia-audit
```

Or import directly in Python:

```python
from agents import AletheiaScoutV2, AletheiaNitpickerV2, AletheiaJudge
from core.runtime_security import normalize_untrusted_text, classify_blocked_intent
from manifest.signing import verify_manifest_signature
```

---

## Architecture

Aletheia operates via a tri-agent consensus model with defense-in-depth input hardening:

```
Incoming Request
│
├─ Schema Validation (Pydantic strict mode, extra="forbid")
├─ Bundle Drift Check (policy version + manifest hash across workers)
├─ Rate Limiting (Upstash Redis distributed / in-memory fallback)
│
├─ Input Hardening
│   ├─ NFKC normalization
│   ├─ Zero-width / control character strip
│   ├─ Bounded URL decode (depth 5)
│   ├─ Bounded Base64 decode (budget 24)
│   ├─ JSON / hex unescape
│   └─ Entropy quarantine (threshold 5.2)
│
├─ Degraded Mode Gate (fail-closed for privileged actions)
├─ Semantic Intent Classification (5 policy categories + coercive detection)
├─ Replay Defense (SHA256 decision token, NX-based idempotent claim)
│
▼
┌─────────────────┐
│   Action Sandbox │  Block subprocess, socket, eval, fs-destroy patterns
└────────┬────────┘
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
│                 │  semantic alias veto, grey-zone escalation
└────────┬────────┘
         │
    PROCEED / DENY
         │
         ▼
   Audit Log + HMAC-Signed TMR Receipt
   (bound to request_id, policy_version, manifest_hash)
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

No auth required. Used by load balancers and uptime monitors.

```json
{
  "status": "ok",
  "manifest_signature": "VALID",
  "uptime_seconds": 3600.0
}
```

`status` is `"degraded"` if manifest signature verification fails. `version` and `mode` are intentionally omitted to reduce information leakage.

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
│   └── utils.py             # Input hardening facade (delegates to core)
├── core/
│   ├── config.py            # Centralized settings (env / yaml / defaults)
│   ├── embeddings.py        # Shared SentenceTransformer service
│   ├── audit.py             # Structured JSON logging + TMR receipts
│   ├── rate_limit.py        # Sliding-window rate limiter (Upstash + in-memory)
│   ├── sandbox.py           # Action sandbox pattern scanner
│   ├── runtime_security.py  # Hardened normalization, intent classifier, schema validation
│   └── decision_store.py    # Distributed replay defense + drift detection
├── manifest/
│   ├── security_policy.json        # Ground truth veto rules (versioned, expires)
│   ├── security_policy.json.sig    # Ed25519 detached signature
│   ├── security_policy.ed25519.pub # Public verification key
│   └── signing.py           # Manifest signing, verification, expiry validation
├── proximity/
│   ├── identity_anchor.py   # Append-only hash chain + replay token tracking
│   ├── proximity_score.py   # Proximity scoring
│   ├── sovereign_relay.py   # Constitutional relay with fail-closed anchoring
│   ├── safety_bounds.py     # Safety boundary enforcement
│   └── spectral_monitor.py  # Spectral health monitoring
├── tests/
│   ├── test_core.py                         # Integration tests
│   ├── test_judge.py                        # Judge unit + adversarial tests
│   ├── test_nitpicker.py                    # Nitpicker unit + semantic tests
│   ├── test_enterprise.py                   # Audit, rate-limit, hardening tests
│   ├── test_hardening.py                    # Sandbox, grey-zone, rotation tests
│   ├── test_signing.py                      # Ed25519 signing/verification + expiry
│   ├── test_judge_manifest.py               # Manifest veto + metadata validation
│   ├── test_security_hardening_v2.py        # XFF, CORS, fail-closed, degraded mode
│   ├── test_runtime_security_layer.py       # Normalization, intent, adversarial, property-based
│   ├── test_distributed_security_integration.py  # Replay, restart, drift tests
│   └── test_proximity/                      # Consciousness proximity module tests
├── simulations/             # Adversarial simulation scripts
├── main.py                  # CLI entry point
├── render.yaml              # Render deployment config
├── vercel.json              # Vercel frontend config
├── Dockerfile               # Docker build (non-root, signature-verified)
├── AGENTS.md                # Agent communication protocol
└── requirements.txt
```

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

---

## Support

If this project is useful to your organization, consider reaching out about our [managed services and enterprise plans](mailto:info@aletheia-core.com).

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ALETHEIA_API_KEYS` | Production | Comma-separated API keys for `X-API-Key` auth. Unset = open mode. |
| `ALETHEIA_RECEIPT_SECRET` | YES (production) | HMAC secret for audit receipts. Service will NOT boot in active mode without this. Generate via `openssl rand -hex 32`. |
| `ALETHEIA_ALIAS_SALT` | RECOMMENDED | Salt for daily alias rotation. Prevents enumeration attacks. Generate via `openssl rand -hex 32`. |
| `ALETHEIA_MODE` | No | `active` (default), `shadow`, or `monitor` |
| `ALETHEIA_LOG_LEVEL` | No | `INFO` (default), `DEBUG`, `WARNING` |
| `ALETHEIA_RATE_LIMIT_PER_SECOND` | No | Requests per IP per second. Default: `10` |
| `UPSTASH_REDIS_REST_URL` | Recommended | Upstash Redis REST endpoint for distributed rate limiting and replay defense. Falls back to in-memory if absent. |
| `UPSTASH_REDIS_REST_TOKEN` | Recommended | Upstash Redis REST token. Required when URL is set. Rotate immediately if exposed. |
| `ALETHEIA_ANCHOR_STATE_PATH` | No | Path for identity anchor state persistence (replay token tracking across restarts). Default: disabled. |
| `ALETHEIA_DECISION_DB_PATH` | No | SQLite path for decision store local fallback. Default: `aletheia_decisions.db`. |
| `CONSCIOUSNESS_PROXIMITY_ENABLED` | No | Enable proximity module. Default: `false` |
| `ALETHEIA_TRUSTED_PROXY_DEPTH` | No | Number of trusted reverse proxies in front of the service. Default: 1 (Render/Vercel). Set to 0 for direct. |
| `ALETHEIA_CORS_ORIGINS` | No | Comma-separated allowed CORS origins. Default: app.aletheia-core.com and aletheia-core.com |

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
# Expected response (v1.5.0+):
# {
#   "status": "ok",
#   "manifest_signature": "VALID"
# }
# Note: version, mode, and uptime removed to prevent information leakage
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
| 2 | Manifest is not expired | Check `expires_at` field in `manifest/security_policy.json` |
| 3 | `ALETHEIA_RECEIPT_SECRET` is set (≥ 32 chars) | `echo ${#ALETHEIA_RECEIPT_SECRET}` |
| 4 | `ALETHEIA_ALIAS_SALT` is set | `echo ${#ALETHEIA_ALIAS_SALT}` |
| 5 | Health endpoint returns `"status":"ok"` | `curl http://localhost:8000/health` |
| 6 | Receipt signature is not `UNSIGNED_DEV_MODE` | Inspect `signature` field in `/v1/audit` response |
| 7 | Tests pass | `pytest tests/ -q` |
| 8 | Private key is NOT in Docker image | `docker run --rm <image> ls /app/manifest/*.key` — must error |
| 9 | Upstash configured for multi-worker | Verify `UPSTASH_REDIS_REST_URL` is set |
| 10 | Degraded mode is observable | Check startup logs for `backend=inmemory` warnings |

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

**ADR-001: Distributed rate limiting with local fallback**
Rate limiting uses Upstash Redis when `UPSTASH_REDIS_REST_URL` is configured, providing distributed sliding-window enforcement across all workers. When Upstash is unavailable, the system falls back to an in-memory limiter that is marked as degraded — privileged actions are denied in this state (fail-closed). This replaces the previous in-memory-only design to support multi-worker production deployments.

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

To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) — Copyright (c) 2026 Ashura Joseph Holeyfield — Aletheia Sovereign Systems
