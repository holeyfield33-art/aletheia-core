# Threat Model — Aletheia Core v1.7.1

Formal enumeration of attack surfaces, trust boundaries, and mitigations.

---

## System Context

Aletheia Core is a **runtime enforcement layer** that interposes between AI agents
and the actions they request. It receives action declarations via HTTP, evaluates
them against a signed policy manifest and semantic models, and returns a
cryptographic receipt with a PROCEED or DENIED decision.

It does **not** execute actions, intercept syscalls, or sandbox process runtime behavior.

---

## Trust Boundaries

```
┌───────────────────────────────────────────────────────────┐
│                    Untrusted Zone                         │
│  AI Agent → HTTP Request → [Internet / LB / Proxy]       │
└──────────────────────────┬────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Aletheia   │  ← Trust Boundary
                    │  Core API   │
                    └──────┬──────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│                    Trusted Zone                           │
│  Signed manifest, embedding model, audit log, key store   │
└───────────────────────────────────────────────────────────┘
```

**Untrusted inputs:** All HTTP request fields (payload, origin, action, headers, IP).
**Trusted artifacts:** Ed25519-signed policy manifest (offline-signed), embedding model weights.
**Operator-controlled:** Environment variables, config files, admin keys.

---

## Attack Surfaces

### 1. Semantic Evasion

**Threat:** Adversary crafts a payload that is semantically equivalent to a blocked
action but falls below the cosine-similarity veto threshold.

**Mitigations:**
- Two-tier veto: primary threshold (0.55) and grey-zone band (0.40–0.55) with keyword heuristics
- 50+ camouflage alias phrases across 6 restricted action categories
- Daily alias bank rotation via HMAC-SHA256(date + manifest_hash + `ALETHEIA_ALIAS_SALT`)
- Action sandbox regex patterns catch explicit dangerous patterns regardless of similarity score

**Residual risk:** A determined adversary with prolonged access could enumerate alias
patterns by observing decision boundaries. An LLM-based classifier (not yet implemented)
would raise the cost further.

### 2. Manifest Tampering

**Threat:** Adversary modifies `security_policy.json` to weaken veto rules.

**Mitigations:**
- Ed25519 detached signature verified before every policy load
- Tampered or missing signature = hard veto, `ManifestTamperedError`, startup refused
- Private key never on runtime host (gitignored, dockerignored)
- Manifest expiry enforced — expired manifests are rejected

**Residual risk:** If the Ed25519 private key is compromised, the adversary can sign
arbitrary manifests. Key rotation procedure documented in `docs/KEY_ROTATION.md`.

### 3. Input Encoding Bypass

**Threat:** Adversary uses Unicode homoglyphs, zero-width characters, Base64 nesting,
or URL encoding to evade pattern matching.

**Mitigations:**
- NFKC normalization collapses homoglyphs
- Unicode TR39 confusable collapsing (Cyrillic/Greek lookalikes → Latin equivalents) via `confusable-homoglyphs`
- Zero-width characters stripped before any agent processing
- Recursive Base64 decode (up to 5 layers, 10× size bomb protection)
- URL percent-encoding decode
- Sandbox patterns match against normalized text
- Shannon entropy quarantine for high-entropy inputs

**Residual risk:** Novel encoding schemes not covered by normalization. Input size
bounded at 10,000 chars by Pydantic validators.

### 4. Timing Oracle on API Keys

**Threat:** Adversary measures response latency to determine which characters of an
API key are correct.

**Mitigations:**
- All API keys compared using `secrets.compare_digest` (constant-time)
- All keys in the set are evaluated before returning (no short-circuit)
- Key store keys hashed with HMAC-SHA256 at rest

**Residual risk:** Negligible — constant-time comparison is the standard countermeasure.

### 5. Rate Limiter Exhaustion

**Threat:** Adversary floods unique IPs to exhaust in-memory rate limiter state.

**Mitigations:**
- 50,000 IP cap with LRU eviction
- Upstash Redis backend available for distributed rate limiting
- Circuit breaker with random jitter on recovery (prevents thundering herd)

**Residual risk:** Without Redis, rate limiter resets on restart. IP-spoofed DDoS
requires proxy-level mitigation (e.g. Cloudflare, CDN WAF).

### 6. Replay Attacks

**Threat:** Adversary replays a previously-allowed audit request to bypass changed policy.

**Mitigations:**
- Decision token derived from SHA-256(request_id | timestamp_iso | policy_version | manifest_hash)
- Token claimed via NX (set-if-not-exists) — first claim wins
- TTL: 1 hour
- Bundle drift detection: mismatched policy_version or manifest_hash across workers rejected

**Residual risk:** Without Upstash Redis, replay defense is per-process only.

### 7. Audit Log Tampering

**Threat:** Adversary with filesystem access modifies audit logs to hide decisions.

**Mitigations:**
- HMAC-SHA256 signed receipts for each decision (receipt integrity independent of log file)
- Audit log file permissions set to `0o600` (owner read/write only)
- Path traversal (`..`) rejected in `ALETHEIA_AUDIT_LOG_PATH`
- PII redacted before writing (email, phone, SSN, credit card patterns)

**Residual risk:** An operator with root access can still modify log files. For
tamper-evident logging, forward audit logs to an append-only external store.

### 8. Sandbox Pattern Bypass

**Threat:** Adversary describes dangerous operations using phrasing that doesn't
match sandbox regex patterns.

**Mitigations:**
- Unicode whitespace normalized before matching (prevents thin-space splitting)
- Zero-width characters removed before pattern scan
- Word-boundary anchored patterns reduce false negatives
- Semantic veto (Judge) provides a second layer for action-level blocking

**Residual risk:** Sandbox operates on declared text, not runtime code. A novel
phrasing not covered by existing patterns may pass. Pair with OS-level sandboxing
(seccomp, AppArmor) for defense in depth.

### 8.1 Unauthorized Tool-Invocation Abuse

**Threat:** Adversary attempts to coerce the system into direct tool execution by
embedding tool-control primitives in payload text (for example `run_in_terminal`,
`apply_patch`, `send_to_terminal`, explicit `tool call`, `function call`, or
tool schema keys such as `recipient_name`/`tool_uses`).

**Mitigations:**
- Semantic pre-screen classifies tool-control instructions as `tool_abuse`
- Sandbox patterns explicitly detect tool-invocation primitives in normalized text
- Action-ID sandbox blocks dangerous tool-oriented action identifiers
- Fail-closed response returns `DENIED` or `SANDBOX_BLOCKED` without internal matcher details

**Residual risk:** Obfuscated or newly invented control vocabulary could still
require pattern-bank updates. Keep regression tests for tool-call abuse payloads
in CI and review denied-event telemetry for drift.

### 9. Information Leakage

**Threat:** Adversary probes responses to learn internal thresholds, pattern names,
or system state.

**Mitigations:**
- Raw threat scores never returned — only discretised bands (LOW/MEDIUM/HIGH/CRITICAL)
- Veto reasons sanitised: similarity scores, matched alias phrases, keyword counts stripped
- Sandbox match pattern names redacted from responses
- `reasoning` field removed from PROCEED responses
- Stack traces never exposed in production mode
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options, Cache-Control

**Residual risk:** Decision latency may leak some information about processing path.

### 10. Config Injection

**Threat:** Adversary on shared host modifies `config.yaml` to weaken thresholds.

**Mitigations:**
- Config ownership validation: rejects files writable by non-owners (`chmod go-w`)
- YAML config bomb protection: 100 KB file size limit
- YAML parse errors logged explicitly, not silently swallowed
- All threshold values validated at startup with range checks and logical consistency
- Invalid values cause fail-fast with actionable error messages

**Residual risk:** An adversary with the same UID as the application process can
modify config files. Run in a dedicated user context.

---

## Out of Scope

The following are explicitly **not** threats that Aletheia Core is designed to mitigate:

| Category | Reason |
|----------|--------|
| Model alignment failures | Aletheia evaluates declared actions, not model internals |
| OS-level process sandboxing | Aletheia validates text, not syscalls |
| Network-level DDoS | Requires proxy/CDN-level mitigation |
| Supply-chain attacks on dependencies | Mitigated by `--require-hashes` in Dockerfile, but not monitored at runtime |
| Social engineering | Out of scope for an automated enforcement layer |

---

## NIST AI RMF Mapping

| NIST Function | Aletheia Mechanism |
|---|---|
| **GOVERN** | Ed25519-signed policy manifests enforce risk tolerance as immutable artefacts |
| **MAP** | Semantic intent classifier categorises requests into 5 risk categories |
| **MEASURE** | HMAC-signed audit receipts provide cryptographically verifiable evidence |
| **MANAGE** | Daily alias rotation, configurable thresholds, active/shadow/monitor modes |
