# Launch Guide (Beginner Friendly)

This guide explains the three easiest ways to run Aletheia Core and how to package it for customers.

## 1) Fastest path: run with Python (no API server)

Use this when you are testing locally or running audits yourself.

```bash
pip install -r requirements.txt
python main.py
```

What this does:
- Runs the tri-agent audit pipeline from `main.py`.
- Prints audit stages and decision in your terminal.

## 2) API path: run with FastAPI wrapper

Use this when you want another app, website, or automation to call Aletheia over HTTP.

```bash
pip install -r requirements.txt
uvicorn bridge.fastapi_wrapper:app --reload
```

Then call it:

```bash
curl -X POST http://127.0.0.1:8000/v1/audit \
  -H "Content-Type: application/json" \
  -d '{"payload":"hello","origin":"trusted_admin","action":"Read_Metadata"}'
```

## 3) Simulation path (security demos)

Use this to demo attack scenarios and defensive behavior.

```bash
PYTHONPATH=. python simulations/adversarial_loop.py
PYTHONPATH=. python simulations/shadow_audit_01.py
PYTHONPATH=. python simulations/lunar_shadow_audit.py
PYTHONPATH=. python simulations/neutral_anchor_audit.py
```

## Which path should you choose?

- Choose **Python-only** if you are learning, prototyping, and validating behavior.
- Choose **FastAPI** if you need integration with frontends, tools, or SaaS workflows.
- Choose **simulations** when pitching security capability to partners/customers.

## Gumroad packaging checklist

1. Create a product zip that includes:
   - Source code
   - `README.md`
   - This guide (`docs/LAUNCH_GUIDE.md`)
   - `LICENSE`
2. Add a short setup PDF (copy/paste Quick Start commands).
3. Add support terms:
   - installation support window (for example, 14 days)
   - what is included vs excluded
4. Publish 2-3 pricing tiers:
   - Starter: source only
   - Pro: source + setup call
   - Team: source + integration support

## Other distribution options

- **Private GitHub repo access** (great for developer buyers).
- **Hosted API subscription** (best recurring revenue if you host it yourself).
- **Consulting bundle** (sell setup + policy tuning services).

## Simple monetization idea

Package this as an "AI Agent Safety Gate" for teams that run automation in finance/ops.

Example offer:
- one-time setup fee
- monthly support retainer
- optional compliance/audit reporting add-on
