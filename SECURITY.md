# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.2.x   | Yes       |
| < 1.2.0 | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Aletheia Cyber-Defense, please report it
responsibly.

**Do not open a public GitHub issue.**

### Contact

Email: **holeyfield33art@users.noreply.github.com**

Include the following in your report:

1. A description of the vulnerability and its potential impact.
2. Steps to reproduce (proof of concept if possible).
3. The version of Aletheia and Python you are using.
4. Any suggested mitigation or fix.

### Response Timeline

- **Acknowledgment:** within 48 hours of receipt.
- **Initial assessment:** within 5 business days.
- **Fix or mitigation:** targeting 14 days for critical issues, 30 days for moderate.

### Disclosure

We follow coordinated disclosure. We will:

1. Confirm the vulnerability and determine its severity.
2. Develop and test a fix.
3. Release the fix and publish a security advisory.
4. Credit the reporter (unless anonymity is requested).

We ask that you do not publicly disclose the vulnerability until a fix has been released.

## Scope

The following are in scope:

- Policy manifest signature bypass or forgery.
- Semantic veto evasion (payloads that should be blocked but are not).
- Sandbox bypass (payloads containing dangerous patterns that pass through).
- Audit log tampering or receipt forgery.
- Input hardening bypass (encoded payloads that evade normalization).
- Rate limiter bypass.
- Stack trace or internal state leakage in production mode.

The following are out of scope:

- Denial of service via resource exhaustion (e.g., sending very large payloads within the 10,000 character limit).
- Issues in third-party dependencies — report those to the upstream project.
- Social engineering attacks.

## Security Design Principles

Aletheia is designed with the following principles:

- **Zero-trust input:** All external data is untrusted by default.
- **Fail closed:** Invalid signatures, missing manifests, and unverifiable actions result in hard denials.
- **Defense in depth:** Multiple independent checks (Scout, Nitpicker, Judge, Sandbox) must all pass.
- **Auditability:** Every decision is logged with a cryptographic receipt.
