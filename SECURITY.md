# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.8.x   | ✅ Yes    |
| 1.7.x   | ✅ Yes    |
| 1.6.x   | ✅ Yes    |
| 1.5.x   | ✅ Yes    |
| < 1.5.0 | ❌ No     |

## Reporting a Vulnerability

If you discover a security vulnerability in Aletheia Core, please report it
responsibly.

**Do not open a public GitHub issue.**

### Contact

Email: **info@aletheia-core.com**

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

## Controls Added in v1.8.0

The following security hardening was applied in v1.8.0 (audit status: PASS, 1018 tests passing, 89% core coverage):

- **Qdrant semantic layer**: Extended pattern matching via vector store after static pattern check. Fail-open on Qdrant errors — static patterns are the safety floor. Block threshold: 0.60.
- **Symbolic narrowing**: Intent bucket pre-filter (action × object) reduces vector search space and improves precision.
- **Per-category thresholds**: `ThresholdsConfig` with tuned cosine-similarity thresholds per intent category (0.82–0.88).
- **Semantic manifest schema**: Pydantic models with threshold validation (0.0–1.0) and duplicate-ID detection.
- **`NitpickerResult` dataclass**: Structured result with `source` field tracking whether block came from static patterns, Qdrant, or both.
- **Production config opt-ins**: `ALETHEIA_ALLOW_ENV_SECRETS` for flexible secret backend deployment. (`ALETHEIA_ALLOW_SQLITE_PRODUCTION` removed in v1.9.0 — production now requires Upstash Redis.)
- **Pre-commit hooks**: ruff lint/format, trailing-whitespace, detect-private-key, version-sync consistency check.
- **51 new tests** covering symbolic narrowing, vector store, semantic manifest schema, thresholds, and duplicate ID validation.

## Controls Added in v1.9.0

The following enterprise hardening was applied in v1.9.0 (audit status: PASS, 1028 tests passing):

- **KeyStore-only authentication**: `ALETHEIA_API_KEYS` env var removed; all API keys managed via encrypted KeyStore with RBAC permissions.
- **RBAC enforcement**: `X-Admin-Key` header removed; admin operations gated by `SECRETS_ROTATE`, `HEALTH_FULL`, `AUDIT_READ` permissions.
- **SQLite blocked in production**: Decision store requires Upstash Redis; `ALETHEIA_ALLOW_SQLITE_PRODUCTION` removed.
- **PII always redacted**: `ALETHEIA_LOG_PII` removed; audit logs never contain PII.
- **AST-based sandbox hardening**: String concatenation bypass detection in code sandbox.
- **Strict Base64 validation**: Rejects non-canonical padding in input hardening.
- **Login failure tracking**: PostgreSQL-backed via Prisma `LoginAttempt` model.
- **Rate limiter circuit breaker**: Allows ~10% probe requests during Redis outages.

## Controls Added in v1.7.0

The following security hardening was applied in v1.7.0 (audit status: PASS, 967 tests passing, 89% core coverage):

- **Config validation:** All security thresholds validated at startup with range checks and logical consistency.
- **HMAC-keyed key hashing:** Key store uses HMAC-SHA256 with `ALETHEIA_KEY_SALT` instead of plain SHA-256.
- **SQLite file permissions:** Decision store and key store databases enforce `0o600` on creation.
- **Audit log hardening:** Path traversal (`..`) rejected; audit log file permissions set to `0o600`.
- **Manifest fail-closed:** Missing `security_policy.json` in active mode raises `RuntimeError`.
- **Timing oracle fix:** API key comparison evaluates all keys before returning (no short-circuit).
- **Proxy depth validation:** `ALETHEIA_TRUSTED_PROXY_DEPTH` validated to 0–5 range at startup.
- **Rate limiter hardening:** Circuit breaker adds random jitter; Redis URL no longer logged.
- **Embedding input validation:** `encode()` rejects empty input, >1,000 texts, or >500 KB total.
- **CSP + Permissions-Policy headers:** Added to FastAPI middleware and `vercel.json`.
- **Sandbox response redaction:** Matched pattern names no longer leaked to clients.
- **PROCEED response hardening:** `reasoning` field removed from PROCEED responses.
- **YAML config bomb protection:** Config loader enforces 100 KB file size limit.
- **Container hardening:** `HEALTHCHECK`, `--timeout-keep-alive`, `--no-create-home`, restrictive `/app/data` permissions.

## Scope Limitations

Aletheia is a **runtime enforcement layer**. It validates declared intents and policy compliance.
It does **not**:

- Intercept syscalls or sandbox process execution at the OS level.
- Replace model alignment, RLHF, or other training-time safety measures.
- Guarantee detection of all adversarial inputs — it raises the cost of attacks.
- Constitute a compliance certification — consult qualified counsel for regulatory requirements.
