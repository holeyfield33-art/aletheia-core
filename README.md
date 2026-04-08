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
  <img src="https://img.shields.io/badge/version-1.6.0-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/tests-527%20passing-brightgreen" alt="Tests"/>
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
│   └── utils.py             # Input hardening (homoglyphs, Base64, URL)
├── core/
│   ├── config.py            # Centralized settings (env / yaml / defaults)
│   ├── embeddings.py        # Shared SentenceTransformer service
│   ├── audit.py             # Structured JSON logging + TMR receipts
│   ├── rate_limit.py        # Sliding-window rate limiter
│   └── sandbox.py           # Action sandbox pattern scanner
├── manifest/
│   ├── security_policy.json        # Ground truth veto rules
│   ├── security_policy.json.sig    # Ed25519 detached signature
│   ├── security_policy.ed25519.pub # Public verification key
│   └── signing.py           # Manifest signing and verification
├── tests/
│   ├── test_core.py         # Integration tests
│   ├── test_judge.py        # Judge unit + adversarial tests
│   ├── test_nitpicker.py    # Nitpicker unit + semantic tests
│   ├── test_enterprise.py   # Audit, rate-limit, hardening tests
│   ├── test_hardening.py    # Sandbox, grey-zone, rotation tests
│   └── test_proximity/      # Consciousness proximity module (84 tests)
├── simulations/             # Adversarial simulation scripts
├── main.py                  # CLI entry point
├── AGENTS.md                # Agent communication protocol
└── requirements.txt
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
| `UPSTASH_REDIS_REST_URL` | Recommended | Upstash Redis REST endpoint for distributed rate limiting. Falls back to in-memory if absent. |
| `UPSTASH_REDIS_REST_TOKEN` | Recommended | Upstash Redis REST token. Required when URL is set. Rotate immediately if exposed. |
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

**ADR-001: In-memory rate limiting only**
Rate limiting is intentionally in-memory and per-process. Adding Redis would introduce a hard runtime dependency that breaks single-binary deployments, adds operational complexity, and is unnecessary for the target deployment model (single-host, proxy-fronted). For horizontal scaling, place a rate-limiting proxy (nginx, Cloudflare, Traefik) in front.

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
