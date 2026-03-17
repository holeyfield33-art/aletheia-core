<p align="center">
  <img src="assets/logo.png" alt="Aletheia Cyber-Defense" width="200"/>
</p>

# 🛡️ Aletheia Cyber-Defense (ACD)

**A 2026-native, multi-agent security framework** designed to protect
autonomous AI systems from instruction smuggling, noise-jamming, and
meta-injections.

In an era where AI agents manage CI/CD pipelines, finance, and operations,
Aletheia provides the **System 2 Reasoning** layer that ensures every
action is verified, traced, and aligned with core intent.

> **Status: Alpha.** Active development. APIs may change.

---

## 🚀 Key Features

- **Polymorphic Defense** — Rotates reasoning methodology to prevent
  prompt-path exploitation and blueprint leakage
- **Structural Intent Analysis (SIA)** — Traces the origin of authority
  for every tool call, neutralizing smuggled instructions in metadata
- **The Judge (Air-Gapped Veto)** — Centralized arbiter that validates
  policy shifts against a cryptographically signed security manifest
- **Swarm-Resistant Triage** — Scout agent clusters diversionary noise
  and prioritizes high-blast-radius threats

---

## 🏗️ Architecture

Aletheia operates via a **Tri-Agent Consensus** model:

```
Incoming Request
│
▼
┌─────────────┐
│    Scout    │  Real-time threat intelligence + swarm detection
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Nitpicker  │  Polymorphic intent analysis + lineage tracing
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Judge    │  Hard veto against signed security manifest
└──────┬──────┘
       │
  PROCEED / DENY
```

---

## 📂 Project Structure

```
aletheia-core/
├── agents/
│   ├── scout_v2.py        # Threat intelligence + swarm detection
│   ├── nitpicker_v2.py    # Polymorphic intent sanitization
│   └── judge_v1.py        # Policy enforcement + hard veto
├── bridge/
│   └── fastapi_wrapper.py # Production REST API
├── manifest/
│   └── security_policy.json  # Ground truth veto rules
├── simulations/
│   ├── adversarial_loop.py   # Adversarial training scenarios
│   └── shadow_audit_01.py    # Real-world attack vectors
├── legal/
│   └── SOVEREIGNTY.md     # Governance principles
├── main.py                # CLI entry point
├── AGENTS.md              # Agent communication protocol
└── requirements.txt
```

---

## 🛠️ Quick Start

```bash
pip install -r requirements.txt
```

Run a local audit (pure Python, no web server required):

```bash
python main.py
```

Start the API server (FastAPI wrapper for HTTP integrations):

```bash
uvicorn bridge.fastapi_wrapper:app --reload
```

Run adversarial simulations:

```bash
PYTHONPATH=. python simulations/adversarial_loop.py
PYTHONPATH=. python simulations/shadow_audit_01.py
PYTHONPATH=. python simulations/lunar_shadow_audit.py
PYTHONPATH=. python simulations/neutral_anchor_audit.py
```

Configure veto rules — edit `manifest/security_policy.json`

---

## 🔒 Security Manifest

The `manifest/security_policy.json` defines immutable veto rules:

| Veto ID | Action Blocked         | Rationale                      |
|---------|------------------------|--------------------------------|
| VETO_01 | Modify_Auth_Registry   | Prevents identity escalation   |
| VETO_02 | Open_External_Socket   | Prevents data exfiltration     |
| VETO_03 | Bulk_Delete_Resource   | Prevents destructive payloads  |

All policy changes require dual-key sign-off.

---

## 🤝 Governance

See `legal/SOVEREIGNTY.md` for the Aletheia Sovereignty Manifest:

- **Agentic Neutrality** — provider agnostic
- **Human Anchor** — manual sign-off on hard veto rules
- **Open Verification** — cryptographically verifiable audit results

---

## 📦 API Reference

**POST** `/v1/audit`

```json
{
  "payload": "string",
  "origin": "trusted_admin | untrusted_metadata | external_file",
  "action": "string",
  "ip": "string"
}
```

Response:

```json
{
  "decision": "PROCEED | DENIED",
  "metadata": {
    "threat_level": 1.2,
    "latency_ms": 14.0,
    "redacted_payload": "string"
  },
  "reasoning": "string"
}
```

---

See `docs/LAUNCH_GUIDE.md` for a beginner-friendly launch and distribution playbook.

## 🔗 Links

- 🌐 Aletheia Sovereign Systems: https://holeyfield33-art.github.io/unitarity-lab
- ☕ Support: https://buymeacoffee.com/holeyfielde
- 🐙 GitHub: https://github.com/holeyfield33-art/aletheia-core

---

© 2026 Aletheia Sovereign Systems — MIT License
