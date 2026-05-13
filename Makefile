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
	python -c "import json, tomllib, sys; p=tomllib.load(open('pyproject.toml','rb'))['project']['version']; j=json.load(open('package.json'))['version']; s=[ln for ln in open('lib/site-config.ts',encoding='utf-8') if 'version:' in ln][0].split(':',1)[1].strip().strip(',').strip().strip('"\''); ok=(p==j==s); print(f'pyproject={p} package.json={j} site-config={s}'); sys.exit(0 if ok else 1)" && echo "Version consistency: OK" || (echo "Version consistency: MISMATCH"; exit 1)
	@echo ""
	@echo "4. Test count check..."
	@count=$$(grep -r -c "def test_" tests/*.py tests/test_proximity/*.py 2>/dev/null | awk -F: '{sum+=$$2} END{print sum}'); \
	echo "Test functions: $$count"; \
	if [ "$$count" -ge 698 ]; then echo "Test count: OK ($$count)"; else echo "Test count: MISMATCH (expected >=698, got $$count)"; fi
	@echo ""
	@echo "=== Verification Complete ==="
