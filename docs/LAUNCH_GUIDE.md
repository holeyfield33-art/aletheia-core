# Launch Guide (Beginner Friendly)

This guide covers every way to install, run, test, and deploy Aletheia Core v1.9.1.

---

## 1) Install from PyPI

```bash
pip install aletheia-cyber-core
```

This installs the `aletheia-audit` CLI command and all Python packages.

## 2) Install from source

```bash
git clone https://github.com/holeyfield33-art/aletheia-core.git
cd aletheia-core
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: Development dependencies

```bash
pip install -e ".[dev]"
```

### Optional: Consciousness Proximity Module

```bash
pip install -r requirements-proximity.txt
export CONSCIOUSNESS_PROXIMITY_ENABLED=true
```

---

## 3) Run locally (no API server)

Use this when you are testing locally or running audits yourself.

```bash
python main.py sign-manifest   # required once before first run
python main.py                 # runs the tri-agent audit pipeline
```

## 4) Run as an API server (FastAPI)

```bash
# Set required secrets
export ALETHEIA_RECEIPT_SECRET=$(openssl rand -hex 32)
export ALETHEIA_ALIAS_SALT=$(openssl rand -hex 32)

# Start the server
uvicorn bridge.fastapi_wrapper:app --host 0.0.0.0 --port 8000
```

Then call it:

```bash
curl -X POST http://127.0.0.1:8000/v1/audit \
  -H "Content-Type: application/json" \
  -d '{"payload":"hello","origin":"trusted_admin","action":"Read_Metadata"}'
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## 5) Run the live demo

```bash
bash demo.sh
```

This starts the server, fires test payloads (safe request, camouflaged attack, sandbox block), and verifies the manifest signature.

## 6) Run security simulations

```bash
PYTHONPATH=. python simulations/adversarial_loop.py
PYTHONPATH=. python simulations/shadow_audit_01.py
PYTHONPATH=. python simulations/lunar_shadow_audit.py
PYTHONPATH=. python simulations/neutral_anchor_audit.py
```

## 7) Run tests

```bash
# Full test suite (1028 tests, requires torch + sentence-transformers)
pytest tests/ -v

# CI-lightweight (skip embedding-dependent tests)
pip install -r requirements-ci.txt
pytest tests/ -v --ignore=tests/test_api.py

# Run only security hardening tests
pytest tests/test_runtime_security_layer.py tests/test_distributed_security_integration.py tests/test_security_hardening_v2.py -v
```

---

## Deploy to Render

One-click:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/holeyfield33-art/aletheia-core)

Manual steps:
1. Connect your GitHub repo in the Render dashboard.
2. Render reads `render.yaml` — it defines the build command, start command, and env vars.
3. Set env vars in the Render dashboard:
   - `ALETHEIA_RECEIPT_SECRET` — `openssl rand -hex 32`
   - `ALETHEIA_ALIAS_SALT` — `openssl rand -hex 32`
   - `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` — required for production (rate limiting, replay defense, decision store)
   - `ALETHEIA_POLICY_THRESHOLD` — threat score cutoff (default `7.5`)
  - API keys are created via `POST /v1/keys` after deployment (KeyStore)
4. Sign the manifest locally (`python main.py sign-manifest`) and commit the `.sig` file before deploying.
5. Verify: `curl https://<your-app>.onrender.com/health`

## Deploy to Vercel (frontend dashboard)

1. Connect the repo in the Vercel dashboard.
2. Vercel reads `vercel.json` — framework is `nextjs`.
3. Set env vars:
  - `ALETHEIA_BACKEND_URL=https://aletheia-core.onrender.com`
  - `ALETHEIA_ALLOWED_BACKEND_HOSTS=aletheia-core.onrender.com,app.aletheia-core.com,aletheia-core.com`
  - `ALETHEIA_DEMO_API_KEY=<value returned by POST /v1/keys>`
  - Optional fallback: `ALETHEIA_API_KEY=<same value>`
4. Deploy. The frontend calls the backend via `/api/demo`.

Note: The demo key should be set on Vercel (server-side route env), not on Render.
Render validates `X-API-Key` against its KeyStore records created via `POST /v1/keys`.

## Deploy with Docker

```bash
# Build
docker build -t aletheia-core .

# Run
docker run -d \
  -p 8000:8000 \
  -e ALETHEIA_MODE=active \
  -e ALETHEIA_RECEIPT_SECRET=$(openssl rand -hex 32) \
  -e ALETHEIA_ALIAS_SALT=$(openssl rand -hex 32) \
  -e UPSTASH_REDIS_REST_URL=<your-upstash-url> \
  -e UPSTASH_REDIS_REST_TOKEN=<your-upstash-token> \
  -e ALETHEIA_POLICY_THRESHOLD=7.5 \
  -v aletheia-data:/data \
  aletheia-core
```

The Dockerfile uses `python:3.11-slim`, verifies the manifest signature at build time, runs as a non-root user, and exposes port 8000.

---

## Which path should you choose?

| Goal | Path |
|------|------|
| Learning, prototyping | Python-only (`python main.py`) |
| Integration with apps, frontends, SaaS | FastAPI server (`uvicorn`) |
| Demo to partners/customers | `bash demo.sh` or simulations |
| Production single-instance | Docker or Render |
| Production multi-worker | Render + Upstash Redis |
| Frontend dashboard | Vercel + Render API backend |
| Library integration | `pip install aletheia-cyber-core` |

---

## Gumroad packaging checklist

1. Create a product zip with: source code, `README.md`, this guide, `LICENSE`.
2. Add a setup PDF with Quick Start commands.
3. Publish 2–3 pricing tiers:
   - **Starter**: source only
   - **Pro**: source + setup call
   - **Team**: source + integration support

## Other distribution options

- **Private GitHub repo access** (great for developer buyers).
- **Hosted API subscription** (best recurring revenue if you host it yourself).
- **Consulting bundle** (sell setup + policy tuning services).

Package this as an **"AI Agent Safety Gate"** for teams that run automation in finance/ops:
- One-time setup fee
- Monthly support retainer
- Optional compliance/audit reporting add-on
