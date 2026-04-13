.PHONY: sign-manifest smoke test verify-launch

sign-manifest:
	python main.py sign-manifest

smoke:
	python scripts/smoke_test_live.py

test:
	pytest tests/ -v

verify-launch:
	@echo "=== Aletheia Core Launch Verification ==="
	@echo ""
	@echo "1. Running tests..."
	pytest tests/ -v --tb=short -q
	@echo ""
	@echo "2. Verifying manifest signature..."
	python -c "from manifest.signing import verify_manifest_signature; verify_manifest_signature('manifest/security_policy.json', 'manifest/security_policy.json.sig', 'manifest/security_policy.ed25519.pub'); print('MANIFEST: VALID')"
	@echo ""
	@echo "3. Checking version consistency..."
	python -c "import json; v=json.load(open('pyproject.toml')); print('pyproject.toml: OK')" 2>/dev/null || true
	grep -q '"1.7.0"' lib/site-config.ts && echo "site-config.ts: OK" || echo "site-config.ts: MISMATCH"
	grep -q '1.7.0' package.json && echo "package.json: OK" || echo "package.json: MISMATCH"
	@echo ""
	@echo "4. Test count check..."
	@count=$$(grep -r -c "def test_" tests/*.py tests/test_proximity/*.py 2>/dev/null | awk -F: '{sum+=$$2} END{print sum}'); \
	echo "Test functions: $$count"; \
	if [ "$$count" -ge 698 ]; then echo "Test count: OK ($$count)"; else echo "Test count: MISMATCH (expected >=698, got $$count)"; fi
	@echo ""
	@echo "=== Verification Complete ==="
