.PHONY: install dev run test lint clean sign-manifest smoke verify-launch

# ── Setup ──────────────────────────────────────────────────────────────────

install:
	pip install -e ".[dev]"

# Install the lightweight CI footprint (no torch/sentence-transformers)
install-ci:
	pip install -r requirements-ci.txt

# ── Development ────────────────────────────────────────────────────────────

dev:
	ALETHEIA_AUTH_DISABLED=true ALETHEIA_MODE=shadow \
	uvicorn server.app:app --host 127.0.0.1 --port 8000 --reload

# ── Production ─────────────────────────────────────────────────────────────

run:
	uvicorn server.app:app --host 0.0.0.0 --port $${PORT:-8000} --workers 2

# ── Testing ────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

test-ci:
	pytest tests/ -v -q --ignore=tests/simulations \
	       --ignore=tests/test_detectors \
	       --ignore=tests/test_api.py

# ── Linting ────────────────────────────────────────────────────────────────

lint:
	python -m mypy core/ server/ agents/ --ignore-missing-imports

# ── Utilities ──────────────────────────────────────────────────────────────

sign-manifest:
	python main.py sign-manifest

smoke:
	python scripts/smoke_test_live.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache *.egg-info

# ── Launch verification (CI gate) ──────────────────────────────────────────

verify-launch:
	@echo "=== Aletheia Core Launch Verification ==="
	@echo ""
	@echo "1. Running tests..."
	pytest tests/ -v --tb=short -q
	@echo ""
	@echo "2. Verifying manifest signature..."
	python -c "from manifest.signing import verify_manifest_signature; \
	  verify_manifest_signature( \
	    'manifest/security_policy.json', \
	    'manifest/security_policy.json.sig', \
	    'manifest/security_policy.ed25519.pub' \
	  ); print('MANIFEST: VALID')"
	@echo ""
	@echo "3. Checking version consistency..."
	python -c " \
	import json, tomllib, sys; \
	p=tomllib.load(open('pyproject.toml','rb'))['project']['version']; \
	j=json.load(open('package.json'))['version']; \
	ok=(p==j); \
	print(f'pyproject={p}  package.json={j}'); \
	sys.exit(0 if ok else 1)" && \
	echo "Version consistency: OK" || (echo "Version consistency: MISMATCH"; exit 1)
	@echo ""
	@echo "=== Verification Complete ==="
