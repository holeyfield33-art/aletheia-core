# Maintainers

This file lists current maintainers of Aletheia Core and the rules for
escalation.

## Active maintainers

| Handle / Role          | Areas                                       | Contact                       |
| ---------------------- | ------------------------------------------- | ----------------------------- |
| `@holeyfield33-art`    | Lead — architecture, releases, security     | maintainers@aletheia-core.com |

Pull request review routing is handled automatically via `.github/CODEOWNERS`.

## Becoming a maintainer

We grow the maintainer team conservatively. Sustained, high-quality
contributions over multiple releases are the path. If you would like to be
considered, sign off on a few PRs in the area you'd like to maintain and
open a `governance` issue with a short proposal.

## Escalation

| Situation                               | Channel                            |
| --------------------------------------- | ---------------------------------- |
| Security vulnerability                  | security@aletheia-core.com (see [SECURITY.md](SECURITY.md)) |
| Code of Conduct incident                | info@aletheia-core.com (see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)) |
| Bug or feature                          | GitHub issue                       |
| Question                                | GitHub Discussions or [SUPPORT.md](SUPPORT.md) |
| Broken hosted demo / production outage  | security@aletheia-core.com         |

## Decision-making

Day-to-day decisions are made via PR review. Larger changes (breaking API
changes, schema migrations that are not backwards-compatible, dependency
upgrades for `next-auth`, `stripe`, `prisma`, or `react`) require **two
maintainer approvals** and a CHANGELOG entry before merge.

## Release authority

Maintainers in the table above may cut a release. Release procedure:
[CONTRIBUTING.md](CONTRIBUTING.md) → "Releases".
