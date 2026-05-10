# Repository Maintenance Checklist

This document tracks ongoing maintenance tasks that keep the Aletheia Core repository healthy, secure, and discoverable.

---

## Daily (5 min)

- [ ] Check GitHub Issues for new bug reports (label: `needs-triage`)
- [ ] Review Discussions for support questions
- [ ] Check CI/CD pipeline status (GitHub Actions)

---

## Weekly (30 min)

### Community
- [ ] Respond to unaddressed issues/PRs (target: <48 hr)
- [ ] Merge PRs from contributors (or request changes)
- [ ] Update MAINTAINERS.md with new active contributors

### Code Quality
- [ ] Run full test suite: `pytest tests/ -v` (may take 10+ min)
- [ ] Check security alerts in GitHub (Settings → Security → Vulnerability alerts)
- [ ] Review CHANGELOG.md for unreleased changes
- [ ] Verify CI passes on main branch

### Documentation
- [ ] Check for broken links in README, docs/
- [ ] Verify all code examples in docs are current
- [ ] Review QUICKSTART.md for accuracy

---

## Monthly (1-2 hours)

### Dependency Management
- [ ] Run `pip list --outdated` to check for updates
- [ ] Review security advisories: `pip-audit` or OWASP Dependency-Check
- [ ] Update requirements.txt with any critical patches
- [ ] Test updated dependencies before merging

### Release Planning
- [ ] Triage GitHub Issues into milestones (vX.Y.Z)
- [ ] Plan next release:  features, bug fixes, breaking changes
- [ ] Update CHANGELOG.md with next version outline

### Performance
- [ ] Profile test suite: `python -m pytest tests/ --durations=10`
- [ ] Identify slow tests (>1s each)
- [ ] File issues for performance optimizations

### Visibility & Growth
- [ ] Check GitHub stars/forks trends
- [ ] Monitor mentions on Twitter, Reddit, Hacker News
- [ ] Respond to questions on StackOverflow tagged with aletheia
- [ ] Share new features in Discussions

---

## Quarterly (4-6 hours)

### Major Release Cycle
- [ ] Decide on semver bump (Major.Minor.Patch)
- [ ] Create release branch: `release/vX.Y.Z`
- [ ] Update version in:
  - `pyproject.toml` (version = "X.Y.Z")
  - `package.json` (version: "X.Y.Z")
  - `CHANGELOG.md` (## [X.Y.Z] - YYYY-MM-DD)
- [ ] Run full test suite (including slow tests)
- [ ] Create GitHub Release with release notes
- [ ] Build & publish:
  - PyPI: `python -m build && twine upload dist/*`
  - Docker: `docker build -t aletheia-core:vX.Y.Z .`
  - npm/cdn (if TypeScript components): `npm publish`

### Audit & Compliance
- [ ] Run static analysis: `bandit -r agents/ core/`
- [ ] Check for security best practices violations
- [ ] Review SECURITY.md (update if needed)
- [ ] Verify LICENSE compliance (check deps)

### Strategic Planning
- [ ] Review RED_TEAM_ANALYSIS.md findings
- [ ] Prioritize next quarter's work (visibility, adoption, features)
- [ ] Update roadmap in CONTRIBUTING.md
- [ ] Plan blog content or demos

---

## Annually (8+ hours)

### Full Audit
- [ ] Security audit (external or detailed internal review)
- [ ] Dependency audit (semver, licensing, vulnerabilities)
- [ ] Documentation audit (completeness, accuracy, examples)
- [ ] Performance baseline (latency, throughput, memory)

### Growth Review
- [ ] Analyze adoption metrics:
  - GitHub stars, forks, contributors
  - PyPI downloads, npm downloads
  - Active discussions, issues, PRs
- [ ] Competitive analysis (compare to LangChain Guard, etc.)
- [ ] Community feedback synthesis (from issues, discussions, surveys)

### Strategic Decisions
- [ ] Roadmap for next year (features, marketing, partnerships)
- [ ] Licensing review (MIT, dual-licensing, commercial options)
- [ ] Infrastructure scaling (CI/CD, artifact storage, SaaS ready)
- [ ] Team & resource allocation

---

## Maintenance Dashboard

### GitHub Metrics (Real-Time)
- **Stars**: https://github.com/aletheia-core/aletheia-core/stargazers
- **Forks**: https://github.com/aletheia-core/aletheia-core/network/members
- **Issues**: https://github.com/aletheia-core/aletheia-core/issues
- **PRs**: https://github.com/aletheia-core/aletheia-core/pulls
- **Actions**: https://github.com/aletheia-core/aletheia-core/actions

### PyPI
- **Page**: https://pypi.org/project/aletheia-core/
- **Download Stats**: https://pypistats.org/packages/aletheia-core
- **Trending**: https://libraries.io/pypi/aletheia-core

### Docker Hub
- **Page**: https://hub.docker.com/r/aletheia/core
- **Pull Stats**: Check Docker Hub dashboard

---

## Common Maintenance Tasks

### Adding a New Maintainer
1. Create issue: "Proposal: add @username as maintainer"
2. Get approval from existing maintainers
3. Update MAINTAINERS.md with new person's info
4. Invite to GitHub organization
5. Add to `@aletheia/maintainers` team
6. Post announcement in Discussions

### Releasing a Patch (v1.9.0 → v1.9.1)
1. Cherry-pick fix commit: `git cherry-pick <commit>`
2. Tag: `git tag v1.9.1`
3. Update CHANGELOG.md with fix details
4. Publish to PyPI and Docker Hub
5. Create GitHub Release with link to CHANGELOG
6. Announce in Discussions

### Handling a Security Issue
1. **DO NOT** post sensitive details in public issues
2. Email security@aletheia-core.dev with details
3. Maintainers assess severity (CVSS score)
4. If critical: create embargoed security advisory
5. Publish fix, then security advisory
6. Update SECURITY.md

### Improving Test Speed
1. Profile tests: `pytest tests/ --durations=10`
2. Identify slow fixtures (e.g., model loading)
3. Create mock fixtures or shared cache
4. Update .pytest.ini for parallelization: `addopts = -n auto`
5. Target: <30 sec for `--quick` mode, <10 min for full suite

### Updating Documentation
1. Review QUICKSTART.md for accuracy
2. Update docs/ with new patterns/features
3. Check code examples run successfully
4. Verify links (internal and external)
5. Rebuild docs site if applicable

---

## Decision Log

Use this section to track major maintenance decisions:

### 2026-05-08: Phase 1 Demo Readiness
- **Decision**: Raise semantic threshold 0.38 → 0.75 to reduce false positives
- **Rationale**: Demo was rejecting benign "system health" and "routine" monitoring queries
- **Trade-off**: May reduce coverage on low-confidence attacks
- **Validation**: Manual testing on real logs shows 10x fewer false positives

### 2026-05-08: Manifest Cache at Startup
- **Decision**: Load all 207 manifest embeddings at startup instead of per-request
- **Rationale**: Eliminate 30s latency on first degraded-mode lookup
- **Implementation**: core/manifest_cache.py + lifespan hook
- **Result**: 30s → <100ms (240x faster)

### 2026-05-08: qdrant-client Version Pin
- **Decision**: Require qdrant-client 1.17.x to match Cloud server
- **Rationale**: 1.15.1 was incompatible with cloud 1.17.1 (protocol changes)
- **Result**: Qdrant integration now stable in production

---

## Questions?

- **Maintenance**: dev@aletheia-core.dev
- **Security**: security@aletheia-core.dev
- **Enterprise**: enterprise@aletheia-core.dev

**Thank you for keeping Aletheia Core healthy!** 🙏
