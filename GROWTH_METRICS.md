# Adoption & Growth Metrics

This document tracks key performance indicators (KPIs) for project health, community engagement, and market adoption.

---

## Baseline (As of 2026-05-10)

### Visibility
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| GitHub Stars | ~150 | 500+ by Q3 | 🔴 Low |
| GitHub Forks | ~20 | 100+ by Q3 | 🔴 Low |
| GitHub Contributors | ~5 | 20+ by Q3 | 🔴 Low |
| Open Issues | ~15 | <10 (healthy) | 🟡 Medium |
| Open PRs | ~3 | <5 (healthy) | 🟢 Good |

### Adoption
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| PyPI Downloads/Month | ~500 | 5K+ | 🔴 Low |
| Docker Hub Pulls | ~200 | 2K+ | 🔴 Low |
| LinkedIn Mentions | ~5 | 50+ | 🔴 Very Low |
| Twitter/X Mentions | ~2 | 20+ | 🔴 Very Low |
| Email Signups | ~10 | 100+ | 🔴 Very Low |

### Repository Health
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Test Coverage | ~78% | >85% | 🟡 Medium |
| CI Pass Rate | ~95% | 100% | 🟡 Medium |
| Avg Issue Response | 48 hrs | <24 hrs | 🟡 Medium |
| Avg PR review | 72 hrs | <24 hrs | 🟡 Medium |
| Last Release | 1.9.0 (2026-04-15) | Monthly | 🟡 OK |
| Documentation | Partial | Complete | 🟡 Medium |

---

## Weekly Tracking

### Google Sheets Template
Copy this template weekly to `docs/metrics/weekly_YYYY-WW.md`:

```
## Week of May 10-16, 2026

### Visibility
- Stars: 150 (+5 vs last week)
- Forks: 20 (no change)
- Contributors: 5 (no change)
- Issues: 15 (no change)

### Engagement
- Discussions posts: 2
- PR reviews: 3
- Issues resolved: 2
- Avg response time: 48 hrs

### Traffic
- Website visits: ~500
- Docs page views: ~300
- Demo link clicks: ~50 (from where?)

### Emerging Trends
- No spike this week
- Next actions: Post on Twitter about X
```

---

## Monthly Review Template

Run this at the end of each month:

### Traffic & Discovery
```bash
# PyPI downloads
curl "https://pypistats.org/api/package/aletheia-core/recent?period=month" | jq

# GitHub traffic (from GitHub Admin → Graphs → Traffic)
# - Visitors: ___
# - Unique Visitors: ___
# - Clones: ___
# - Referrers (top 5):
#   1. Google (___%)
#   2. GitHub (___%)
#   3. ...

# Search keywords (from Google Search Console)
# Top keywords driving traffic:
# - prompt injection guard
# - AI safety
# - ...
```

### Community Growth
```bash
# GitHub stats
gh repo view aletheia-core/aletheia-core --json stargazerCount,forkCount,pullRequests,issues

# Compare to same month last year (if applicable)
# YoY Growth: ____%
```

### Competitive Positioning
| Competitor | Stars | Downloads/mo | Momentum |
|-------------|-------|------|----------|
| LangChain Guard | 2K | 50K | Rising 📈 |
| Constitutional AI | 1.2K | 10K | Stable ➡️ |
| Rebuff.AI | 500 | 5K | Stable ➡️ |
| **Aletheia Core** | **150** | **500** | **Rising 📈** |

---

## Adoption Barriers (From RED_TEAM_ANALYSIS.md)

### Current Obstacles
1. ❌ No live demo (users must clone + install)
2. ❌ README headline unclear (no hook)
3. ❌ No GitHub practices (no discussions, templates)
4. ❌ Slow tests block contributions
5. ❌ Zero marketing (silent shipping)
6. ❌ Docs too technical (for architects, not users)
7. ❌ No pricing clarity
8. ❌ No CI/CD badge

### Removal Plan (4 Weeks, ~40 hours)

**Week 1: High Impact** (6 hours)
- [ ] Create live demo on Vercel / Replit
- [ ] Rewrite README headline & add CTA
- [ ] Set up GitHub Discussions + issue templates

**Week 2: Enabling** (6 hours)
- [ ] Optimize test suite for speed (<30 sec --quick)
- [ ] Add CI/CD badge to README
- [ ] Create QUICKSTART.md (instead of 800-line README)

**Week 3: Credibility** (6 hours)
- [ ] Publish blog post: "How We Block AI Attacks (Without Hallucinating)"
- [ ] Create 5-min demo YouTube video
- [ ] Post on Twitter, LinkedIn, Hacker News

**Week 4: Community** (6 hours)
- [ ] Host live Q&A session
- [ ] Collect user testimonials for README
- [ ] Create roadmap for next quarter (public)

---

## Success Criteria

### 1-Month Target (by June 10, 2026)
| Metric | Target | Rationale |
|--------|--------|-----------|
| Stars | 300+ | 2x baseline |
| PyPI Downloads | 2K+/mo | 4x baseline |
| Contributors | 10+ | 2x baseline |
| Issues Response | <24 hrs | Faster community perception |
| Live Demo | Ready | Lower barrier to trial |
| Discussions | 20+ posts | Community engagement |

### 3-Month Target (by August 10, 2026)
| Metric | Target | Rationale |
|--------|--------|-----------|
| Stars | 500+ | Visible on GitHub trending |
| PyPI Downloads | 5K+/mo | Emerging mainstream adoption |
| Contributors | 20+ | Active community |
| Blog Followers | 100+ | Thought leadership |
| Company Partnerships | 1+ | Market credibility |

### 6-Month Target (by November 10, 2026)
| Metric | Target | Rationale |
|--------|--------|-----------|
| Stars | 1K+ | Recognized in industry |
| PyPI Downloads | 10K+/mo | Strong adoption |
| Contributors | 50+ | Thriving community |
| SaaS Beta | Active | Product line extension |
| Press Mentions | 5+ | Media visibility |

---

## Activation Channels

### Organic (Low Cost, Slow)
- 📝 Blog posts on DEV.to, Medium, Hashnode
- 💬 Reddit: r/MachineLearning, r/Python, r/learnprogramming
- 🐦 Twitter/X thread strategy (weekly tips)
- 💌 Email newsletter (security updates + features)
- 🎓 Academic discussion (arXiv, conferences)

### Paid (Fast, Measured)
- 🎯 Google Ads (for "prompt injection" keywords)
- 🎯 LinkedIn Ads (targeting AI security professionals)
- 🎯 Dev.to sponsored posts
- 🎯 HackerNews top banner

### Partnerships (High Impact, Slower)
- 🤝 LangChain Guard (comparison table, not attack)
- 🤝 OpenAI platform docs (referral link)
- 🤝 Security conferences (booth, talk)
- 🤝 Enterprise security platforms (white-label)

### Community (High Stickiness)
- 🎉 GitHub Discussions for q&a
- 🎉 Monthly livestream Q&A sessions
- 🎉 User testimonials + case studies
- 🎉 Contributor recognition (MAINTAINERS.md)

---

## Competitive Advantages to Highlight

### vs LangChain Guard
- ✨ Better at system-prompt attacks (specific patterns)
- ✨ Faster startup (manifest cache)
- ✨ Lower false positives (tuned threshold)
- ⚠️ Smaller community (not yet competitor advantage)

### vs Constitutional AI
- ✨ Production-ready with audit trail
- ✨ Works locally + offline (no API calls)
- ⚠️ Single-purpose vs broader framework

### vs Rebuff.AI
- ✨ Open source (full transparency)
- ✨ Ed25519 signed receipts (legal defensibility)
- ⚠️ Smaller team (not yet Enterprise features)

---

## Growth Levers to Pull

### 1. Content (Weeks 1-3)
- Blog: "Why Prompt Injection Defenses Keep Failing"
- Video: 5-min demo + how-it-works
- Slides: 20-slide deck for conferences

### 2. Demo (Weeks 1-2)
- Live SandBox: Enter a jailbreak, see it blocked
- Benchmark: Attack database + detection rate graph
- Comparison: Our score vs 3 competitors

### 3. SEO (Weeks 2-4)
- Blog posts optimized for: "prompt injection", "AI safety", "agent security"
- Backlinks: Reach out to security blogs for mentions
- Schema: Structured data for GitHub, docs

### 4. Social Proof (Weeks 3-4)
- Testimonials from early users (2-3)
- Company logos (e.g., "Used by X, Y, Z")
- Media mentions (even small blogs count)

---

## Measuring Success

### North Star: Adoption Rate

```
30-Day New Users = (PyPI installs month N - month N-1) / total potential market
```

- **Q2 Target**: 20% of active AI dev community tries it
- **Q3 Target**: 50% awareness + 20% trial rate

### Key Insight Questions

1. **Who is adopting?** (Job titles, company size, use case)
2. **Why do they adopt?** (Feature, word-of-mouth, search result)
3. **Why don't they stay?** (Bugs, friction, missing features)
4. **Who is *not* adopting?** (Competitors' users, enterprises)

**Action**: Create survey in QUICKSTART.md feedback link:
```
"Have 2 min? Help us improve: [Feedback Survey](https://forms.gle/...)"
```

---

## Next Steps

1. **This Week**: Review this metrics doc, pick 3 monthly targets
2. **This Month**: Implement adoption barriers removal plan (Week 1 from RED_TEAM_ANALYSIS.md)
3. **Next Month**: Measure progress against targets, adjust channel spend

---

**Owner**: @maintainers
**Last Updated**: 2026-05-10
**Next Review**: 2026-06-10
