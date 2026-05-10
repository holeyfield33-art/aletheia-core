# GitHub Issue Templates & PR Guidelines

## Issue Categories

### Security Issue
**Use this for security vulnerabilities.** Do NOT post sensitive details publicly; email security@aletheia-core.dev instead.

### Feature Request
**Use this for new functionality.** e.g., "Support custom embedding models" or "Add rate-limiting dashboard"

### Bug Report
**Use this for defects.** e.g., "False positive on 'system health check'" or "Qdrant connection timeout on startup"

### Documentation
**Use this for docs improvements.** e.g., "Add example of batch auditing" or "Clarify config options"

### Performance Issue
**Use this for speed/memory problems.** e.g., "Test discovery takes 30+ seconds"

---

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Fork the repo and create a feature branch (`git checkout -b feature/your-idea`)
- [ ] Make atomic, well-commented commits
- [ ] Run linting: `ruff check . --fix`
- [ ] Run type checks: `mypy . --strict`
- [ ] Run tests: `./scripts/watch-tests.sh --quick` (fast path)
  - For full suite: `pytest tests/ -v` (slower, full validation)
- [ ] Add tests for new functionality (code coverage target: >85%)
- [ ] Update docstrings per Google style
- [ ] Commit message format:
  ```
  fix: trim semantic blocks from false positives

  - Remove 5 generic "system" entries that matched benign queries
  - Add 5 specific "reveal system prompt" variants
  - Update threshold from 0.38 to 0.75 with rationale

  Refs: issue #123
  ```

---

## Code Style

- **Python**: PEP 8, via ruff
- **Type Hints**: Use `pyright --strict` (no `Any` without explanation)
- **Docstrings**: Google style (3 lines: summary, args, returns)
- **Tests**: Pytest with descriptive names
- **Formatting**: 88-char line length (Black default)

---

## Review Process

1. **Automated**: Pre-commit hooks (ruff, mypy, trailing whitespace)
2. **CI**: GitHub Actions runs full test suite + linting
3. **Human Review**: Maintainers assign reviewer, 48-72 hour turnaround
4. **Merge**: Squash commits, update CHANGELOG.md

---

## Common Contribution Types

### Adding a Semantic Pattern

1. Edit `data/semantic_manifest.json`
2. Add entry with unique `id`, `text`, `category`, `severity`
3. Add corresponding test in `tests/test_judge_v1.py`
4. Run: `python scripts/index_qdrant_manifest.py` (if Qdrant enabled)
5. Commit with rationale: "feat: add pattern for 'override consensus'"

### Fixing a False Positive

1. Create issue with example payload + false positive reason
2. Find the problematic entry in `data/semantic_manifest.json`
3. Remove or narrow the entry; add new tests
4. Verify with: `pytest tests/test_nitpicker_v2.py -v -k "false_positive"`
5. Document the fix in PR

### Performance Improvement

1. Profile the code: `python -m cProfile -s cumulative main.py`
2. Identify bottleneck (e.g., embedding model loading)
3. Create fix with before/after metrics in PR description
4. Add benchmark test: `tests/test_performance.py`
5. Target: 10% improvement minimum

---

## Recognition

All contributors are listed in [MAINTAINERS.md](../MAINTAINERS.md) + GitHub Contributors page.

Top contributors (10+ merged PRs) get:
- ⭐ Featured in README "Supporters" section
- 💬 Mention in monthly newsletter
- 🎁 Exclusive early access to SaaS beta

---

## Questions?

- 💬 Ask in [GitHub Discussions](https://github.com/aletheia-core/aletheia-core/discussions)
- 📧 Email: dev@aletheia-core.dev
- 🏢 Enterprise support: enterprise@aletheia-core.dev

**Thank you for helping secure AI agents!** 🎉
