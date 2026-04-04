<p align="center">
  <img src="assets/logo.png" alt="Aletheia Cyber-Defense" width="180"/>
</p>

<h1 align="center">Aletheia Cyber-Defense (ACD)</h1>

<p align="center">
  <strong>Enterprise-Grade System 2 Security for AI Agents</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.2.2-blue" alt="Version"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/tests-265%20passing-brightgreen" alt="Tests"/>
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
| 5 | **Daily alias rotation** | Semantic alias phrase order is deterministically shuffled daily (SHA-256 seed from date + manifest hash) to prevent reverse-engineering via probing. |
| 6 | **Embedding pre-warming** | Model loaded eagerly at FastAPI startup to eliminate cold-start latency on the first request. |
| 7 | **Audit trail integrity** | Every decision produces a structured JSON log line and an HMAC-signed TMR receipt (decision + policy hash + signature). |
| 8 | **Input hardening** | NFKC homoglyph collapse, zero-width character strip, recursive Base64 decode, and URL percent-encoding decode — all applied before any agent sees the payload. |
| 9 | **Rate limiting** | In-memory sliding-window limiter, default 10 requests per second per IP. |
| 10 | **No stack-trace leakage** | Global FastAPI exception handler returns an opaque error in production mode. |
| 11 | **Config-driven defense modes** | `active` / `shadow` / `monitor` — switchable via environment variable or `config.yaml` without code changes. |

---

## Key Features

- **Cryptographic Policy Integrity** — Ed25519-signed security manifest; tamper triggers an instant hard veto
- **Semantic Intent Analysis** — Cosine similarity replaces string matching; catches camouflaged fund transfers, privilege escalation, and data exfiltration
- **Grey-Zone Second-Pass Classifier** — Keyword heuristics catch creative paraphrases that fall below the primary threshold
- **Action Sandbox** — Pattern-based scanner blocks subprocess, eval, raw socket, and filesystem-destruction payloads
- **Polymorphic Defense** — Config-driven deterministic rotation across LINEAGE, INTENT, and SKEPTIC modes
- **Structured Audit Trail** — JSON-line logging with HMAC-signed TMR receipts on every decision
- **Rate Limiting** — Sliding-window limiter (10 req/s per IP, configurable)
- **Input Hardening** — Homoglyph normalization, Base64 and URL-encoding recursive decode, control-character strip
- **Daily Alias Rotation** — Alias bank order shuffled deterministically per day to resist probing
- **Swarm-Resistant Triage** — Scout agent clusters diversionary noise and prioritizes high-blast-radius threats

---

## Quick Start

### Install

```bash
pip install -r requirements.txt
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
pytest tests/ -v
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
  "origin": "trusted_admin | untrusted_metadata | external_file",
  "action": "string",
  "ip": "string"
}
```

Response:

```json
{
  "decision": "PROCEED | DENIED | RATE_LIMITED | SANDBOX_BLOCKED",
  "metadata": {
    "threat_level": 1.2,
    "latency_ms": 14.0,
    "redacted_payload": "string",
    "client_id": "ALETHEIA_ENTERPRISE"
  },
  "receipt": {
    "decision": "PROCEED",
    "policy_hash": "sha256...",
    "signature": "hmac-sha256...",
    "issued_at": "ISO-8601"
  }
}
```

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
│   ├── test_core.py         # Integration tests (18)
│   ├── test_judge.py        # Judge unit + adversarial tests (13)
│   ├── test_nitpicker.py    # Nitpicker unit + semantic tests (8)
│   ├── test_enterprise.py   # Audit, rate-limit, hardening tests (9)
│   └── test_hardening.py    # Sandbox, grey-zone, rotation tests (15)
├── simulations/             # Adversarial simulation scripts
├── main.py                  # CLI entry point
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

- **Rate limiter is in-memory.** State resets on process restart and does not synchronize across workers. Use Redis or an external store for horizontal scaling.
- **Embedding model requires ~500 MB on disk.** The `all-MiniLM-L6-v2` model is downloaded on first use. Pre-pull in your Docker image build step.
- **Static alias bank.** While daily rotation mitigates probing, a determined adversary with prolonged access could enumerate patterns. Consider supplementing with an LLM-based classifier for high-sensitivity deployments.
- **No runtime syscall interception.** The action sandbox validates declared intents, not runtime behavior. Pair with OS-level sandboxing (seccomp, AppArmor) for defense in depth.

---

## Support

If this project is useful to your organization, consider supporting its development:

- [GitHub Sponsors](https://github.com/sponsors/holeyfield33-art)
- [Buy Me a Coffee](https://buymeacoffee.com/holeyfielde)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues and pull requests.

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) — Copyright (c) 2026 Ashura Joseph Holeyfield — Aletheia Sovereign Systems
