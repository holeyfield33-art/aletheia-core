# Maintainer Chore List

A lightweight, repeatable checklist for keeping `aletheia-core` healthy. The
**Daily** section is the fast pass; **Weekly** and **As-needed** capture the
slower-moving hygiene work. Commands assume the repo root and a Python 3.11/3.12
environment.

## Daily (≈5 minutes)

- [ ] **CI is green on `main` and open PRs.** Skim the Actions tab for red runs.
      Pay attention to the always-on gates: `test (3.11)`, `test (3.12)`,
      `test-coverage`, `Red-team adversarial suite`, `Semgrep SAST`,
      `Bandit SAST`, `pip-audit`, `npm audit`, and `Env var inventory drift check`.
- [ ] **Env var docs are in sync.** Any new `os.getenv` / `env_bool` /
      `process.env` reference must be reflected in `docs/ENVIRONMENT_VARIABLES.md`:
      ```
      node scripts/ci/check-env-consistency.mjs --check=all
      ```
- [ ] **Dependency vulnerabilities (CI-blocking subset).** This is what the PR
      gate enforces:
      ```
      pip-audit -r requirements-ci.txt --strict --no-deps
      ```
- [ ] **Triage Dependabot / bot PRs.** Merge clean patch bumps; defer majors to
      the weekly dependency review below.

## Weekly (≈30 minutes)

- [ ] **Full dependency audit (lockfile).** Catches transitive vulns the CI
      subset does not:
      ```
      pip-audit -r requirements.txt --no-deps
      npm audit --omit=dev
      ```
      For fixes that touch the hash-pinned lockfile, regenerate properly rather
      than hand-editing interdependent packages:
      ```
      pip-compile --allow-unsafe --generate-hashes \
        --output-file=requirements.txt requirements.in
      ```
      Hand-editing is only safe for leaf packages with no install-time
      dependencies (e.g. `idna`, `urllib3`); anything with its own constraints
      (`starlette`↔`fastapi`, `transformers`↔`torch`, `pillow`) must go through
      `pip-compile` + a full test run.
- [ ] **Run the suite locally across both Pythons** before large merges:
      ```
      python -m pytest -q
      ```
- [ ] **Lint + compile sanity:**
      ```
      ruff check .
      python -m compileall core agents guards detectors manifest crypto
      ```
- [ ] **Dead-code sweep.** Spot-check for unused symbols/files introduced during
      the week (zero-call-site helpers, orphaned prototypes).

## As-needed

- [ ] **Secret/key rotation drills** for receipt + manifest signing keys
      (`ALETHEIA_RECEIPT_*`, `ALETHEIA_MANIFEST_EXPECTED_KEY_ID`).
- [ ] **Review `ENVIRONMENT`-gated behavior** when adding production guards so
      tests that depend on dev/test env values do not silently fail-closed.
- [ ] **Node runtime deprecations.** GitHub Actions is warning that several
      pinned actions still target Node 20; bump `actions/checkout`,
      `actions/setup-node`, `actions/setup-python`, and `actions/cache` when
      convenient.

## Outstanding items (as of 2026-06-27)

These predate the current dead-code cleanup branch and are tracked here so they
are not lost. None are introduced by that PR.

### Dependency vulnerabilities still open in `requirements.txt`

The CI-blocking set (`requirements-ci.txt`) is clean. The full lockfile still
reports vulnerabilities that require a dedicated dependency-refresh PR (major
bumps, prerelease-only fixes, or `fastapi`/`torch` constraint resolution — not
safe to smuggle into unrelated PRs):

| Package | Current | Fix | Notes |
| --- | --- | --- | --- |
| pillow | 10.4.0 | 12.2.0 | Major jump (10 → 12); validate image paths. |
| transformers | 4.55.4 | 5.0.0rc3 / none | Several advisories; only fix is a major prerelease. Pin/evaluate carefully. |
| starlette | 1.0.0 | 1.3.1 | Constrained by `fastapi`; bump both together. |
| torch | 2.11.0 | none yet | CVE-2025-3000 has no released fix; monitor. |

Already cleared on the cleanup branch: `cryptography 46.0.7 → 48.0.1`,
`idna 3.13 → 3.15`, `urllib3 2.6.3 → 2.7.0`.

### Pre-existing test failures (unrelated to dead-code cleanup)

- `tests/test_manifest_cache.py::TestLoadAndEmbedManifest::test_load_and_embed_manifest_success`
  — the test's `_StubModel.encode()` does not accept `convert_to_numpy`, which
  `core/manifest_cache.py` passes. Update the stub (or the call) so the contract
  matches. Affects `test (3.11)` and `test-coverage`.
- `tests/test_api.py::TestAuditEndpointShadowMode::test_shadow_mode_overrides_deny_to_proceed`
  — fails because the runner's `ENVIRONMENT` is empty, so shadow mode
  fail-closes (`SHADOW_MODE_BLOCKED`) instead of overriding `DENIED`. The test
  needs an explicit dev/test `ENVIRONMENT` value. Affects the
  `Red-team adversarial suite` job.
