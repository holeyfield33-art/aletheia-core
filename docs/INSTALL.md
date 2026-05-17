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
ALETHEIA_RECEIPT_SECRET=<32+ chars>
ALETHEIA_KEY_SALT=<32+ chars>
ALETHEIA_ALIAS_SALT=<32+ chars>
# One redis backend is required in production:
# REDIS_URL=<rediss-url>
# or
# UPSTASH_REDIS_REST_URL=<upstash-url>
# UPSTASH_REDIS_REST_TOKEN=<upstash-token>

# If using postgres backend in production:
# ALETHEIA_DATABASE_BACKEND=postgres
# DATABASE_URL=<postgres-url-with-sslmode=require>

# If staying on sqlite in production, explicit opt-in is required:
# ALETHEIA_ALLOW_SQLITE_PRODUCTION=true

# If using env secrets backend in production, explicit opt-in is required:
# ALETHEIA_ALLOW_ENV_SECRETS=true
```

If you also configure Ed25519 receipt signing keys, set either
`ALETHEIA_RECEIPT_PRIVATE_KEY` or `ALETHEIA_RECEIPT_PRIVATE_KEY_PATH`.

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
uvicorn server.app:app --host 0.0.0.0 --port 8000
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
