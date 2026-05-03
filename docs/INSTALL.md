# Installation Guide

Step-by-step self-hosted installation for Aletheia Core.

## 1. Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (optional, for dependency services)
- PostgreSQL (recommended for production)
- Redis (required for production)

## 2. Clone and bootstrap

```bash
git clone https://github.com/holeyfield33-art/aletheia-core.git
cd aletheia-core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

## 3. Configure environment

Copy and edit environment values:

```bash
cp .env.example .env
```

Required production baseline:

```bash
ENVIRONMENT=production
ALETHEIA_MODE=active
ALETHEIA_RECEIPT_PRIVATE_KEY=<PEM>
ALETHEIA_KEY_SALT=<32+ chars>
ALETHEIA_ALIAS_SALT=<32+ chars>
DATABASE_URL=<postgres-url>
REDIS_URL=<rediss-url>
```

If you still need to verify older HMAC receipts during retention, also set
`ALETHEIA_RECEIPT_SECRET`.

See [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md) for the full matrix.

## 4. Sign policy manifest

```bash
python main.py sign-manifest
```

## 5. Run dependency services (optional local)

```bash
docker compose up -d postgres redis qdrant
```

## 6. Run backend and frontend

Backend:

```bash
uvicorn bridge.fastapi_wrapper:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
npm run dev
```

## 7. Verify health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## 8. Run tests

```bash
pytest tests/ -v --tb=short
npm test
```
