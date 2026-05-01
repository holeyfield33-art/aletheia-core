# Contributing to Aletheia Core

Thank you for your interest in improving Aletheia. This document outlines how to
contribute effectively.

## Getting Started

1. Fork the repository and clone your fork.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```
4. Sign the security manifest (required for tests to pass):
   ```bash
   python main.py sign-manifest
   ```
5. Run the test suite to confirm your environment works:
   ```bash
   pytest tests/ -v --ignore=tests/test_api.py
   ```

### Proximity module tests (optional)

The consciousness proximity module has separate dependencies:

```bash
pip install -r requirements-proximity.txt
pytest tests/test_proximity/ -v
```

## Development Workflow

1. Create a branch from `main` for your change.
2. Make your changes. Follow the conventions below.
3. Run the full test suite (`pytest tests/ -v --ignore=tests/test_api.py`) and ensure all tests pass.
4. Run the full test suite (`pytest tests/ -v --ignore=tests/test_api.py`) and ensure all tests pass.
5. Commit with a [conventional commit](https://www.conventionalcommits.org/) message:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for test additions or changes
   - `chore:` for maintenance tasks
6. Open a pull request against `main`.

### Developer Certificate of Origin (DCO)

This repository currently does not enforce DCO with a bot workflow. Contributors
must sign off each commit manually:

```bash
git commit -s -m "<type>: <summary>"
```

Every commit in a pull request should include a `Signed-off-by:` trailer.

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`. They enforce:

- **ruff** lint and format checks
- Trailing whitespace and end-of-file fixes
- YAML/JSON syntax validation
- Private key detection
- Version consistency across `pyproject.toml`, `main.py`, `bridge/fastapi_wrapper.py`, and `package.json`

If a hook modifies files (e.g. ruff auto-fix), re-stage and commit again.

### Controlled Dependency Upgrades (Breaking Changes)

When `npm audit` or `npm outdated` indicates fixes that require major version
bumps, use this staged process:

1. Create a dedicated branch, e.g. `chore/deps-major-<area>`.
2. Capture baseline before changes:
   - `npm test`
   - `pytest -q`
3. Upgrade one risk group at a time:
   - Runtime frameworks (`next`, `react`, `react-dom`, `next-auth`)
   - Tooling (`vitest`, `eslint`, `typescript`)
   - Data layer (`prisma`, `@prisma/client`)
4. After each group, run focused suites first, then full suites.
5. Document migration notes in the PR description:
   - Breaking API changes
   - Config updates
   - New warnings or ignored advisories
6. Use `npm audit fix --force` only inside these dedicated major-upgrade branches,
   never in routine maintenance branches.

### PR Labels

Use these labels on PRs for automatic release-drafter categorization:

- `feature` / `enhancement` — Features
- `fix` / `bug` — Bug Fixes
- `security` — Security
- `chore` / `refactor` — Maintenance
- `dependencies` — Dependencies
- `documentation` — Documentation

## Code Conventions

- **Python 3.10+** — use type hints on all public function signatures.
- **Pure Python** — minimize external dependencies. Justify any new dependency in the PR description.
- **Security comments** — annotate any security-critical code path with a clear comment explaining the rationale.
- **No stack traces in production** — all exceptions must be caught at API boundaries.

## Testing

- Add tests for every new feature or bug fix.
- Adversarial test cases are encouraged — include payloads that should be blocked and payloads that should pass.
- Place tests in the appropriate file (`test_judge.py`, `test_nitpicker.py`, `test_enterprise.py`, `test_hardening.py`) or create a new file under `tests/` if the scope warrants it.

## Security Policy

If you discover a security vulnerability, **do not open a public issue**. Follow the
process described in [SECURITY.md](SECURITY.md).

## Manifest Changes

If you modify `manifest/security_policy.json`, you must re-sign the manifest:

```bash
python main.py sign-manifest
```

Commit both the updated JSON and the new `.sig` file.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE).
