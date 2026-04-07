# Agent Architecture — Aletheia Core

This document describes the three agents that form the Aletheia Core tri-agent pipeline.
All agents are implemented and active. Claims here reflect the actual code.

---

## 1. Scout (`agents/scout_v2.py`)

**Role:** Threat intelligence and swarm-detection pre-filter.

**What it actually does:**
- Matches payloads against known instruction-smuggling prefixes (e.g. `SYSTEM_UPDATE:`, `EMBEDDED_SHELL:`)
- Checks for sensitive exfiltration patterns (`merger clause`, `private_key`)
- Detects contextual camouflage: neutral anchors (`refactor`, `routine`) combined with high-value targets (`transfer`, `auth`, `key`)
- Detects rapid meta-querying from a single source (> 5 requests in 60 seconds = rotation probing)
- Caps internal `_query_history` at 10,000 entries with LRU eviction

**Output:** `(threat_score: float, report: str)`. Score ≥ `ALETHEIA_POLICY_THRESHOLD` (default 7.5) causes a DENIED decision.

**What it does NOT do:**
- Does not make network calls or query external threat feeds
- Does not block on its own — Scout score feeds the decision logic in `fastapi_wrapper.py`

---

## 2. Nitpicker (`agents/nitpicker_v2.py`)

**Role:** Polymorphic intent sanitizer with semantic embedding analysis.

**What it actually does:**
- Detects imperative-alias prefixes (`routine:`, `cleanup:`, `refactor:`) that camouflage command sequences
- Runs cosine-similarity check against 18 blocked semantic patterns (e.g. "bypass authentication", "exfiltrate data externally") using `all-MiniLM-L6-v2` embeddings. Threshold: 0.45.
- Applies one of three deterministic rotation modes (`LINEAGE`, `INTENT`, `SKEPTIC`) to vary sanitization behavior:
  - **LINEAGE:** Passes only if `source_origin == "trusted_admin"`, otherwise redacts
  - **INTENT:** Regex-redacts restricted verbs (`update`, `bypass`, `delete`, `override`)
  - **SKEPTIC:** Full redaction if `SYSTEM_UPDATE` appears in the payload

**What it does NOT do:**
- Does not make final PROCEED/DENY decisions — that is the Judge's responsibility
- Sanitized output is used for logging; the original payload is passed to the Judge for veto checks

---

## 3. Judge (`agents/judge_v1.py`)

**Role:** Cryptographic policy enforcer and semantic veto engine.

**What it actually does:**
- Verifies the Ed25519 detached signature on `manifest/security_policy.json` before loading policy. Raises `ManifestTamperedError` on failure — hard veto, no fallback.
- Checks `action_id` against `restricted_actions` in the policy manifest (exact string match)
- Runs cosine-similarity veto against 50+ semantic alias phrases across 6 restricted action categories (Transfer_Funds, Approve_Loan_Disbursement, Modify_Auth_Registry, Initiate_ACH, Open_External_Socket, Bulk_Delete_Resource)
- Two-tier veto: primary threshold (0.55) and grey-zone band (0.40–0.55) with keyword heuristics (≥ 2 hits = veto)
- Daily alias bank rotation: order shuffled by HMAC-SHA256(date + manifest_hash + `ALETHEIA_ALIAS_SALT`). Without `ALETHEIA_ALIAS_SALT`, falls back to plain SHA-256 with a logged warning — rotation is predictable in that case.

**Output:** `(is_allowed: bool, message: str)`

---

## 4. Pipeline Execution Order

```
Request → Schema Validation (Pydantic strict, extra="forbid")
        → Bundle Drift Check (policy_version + manifest_hash)
        → Rate Limiting (Upstash Redis / in-memory fallback)
        → Input Hardening (NFKC, URL/Base64 decode, unescape, entropy quarantine)
        → Degraded Mode Gate (fail-closed for privileged actions)
        → Semantic Intent Classification (5 categories + coercive detection)
        → Replay Defense (SHA256 decision token, NX-based claim)
        → Sandbox check (check_action_sandbox)  ← blocks dangerous patterns
        → Scout.evaluate_threat_context()        ← threat scoring
        → Nitpicker.sanitize_intent()            ← polymorphic sanitization
        → Judge.verify_action()                  ← manifest + semantic veto
        → Decision (PROCEED / DENIED)
        → log_audit_event() + build_tmr_receipt()
```

---

## 5. Design Principles

- **Zero-Trust Input:** All external data is untrusted by default. Input hardening runs before any agent sees the payload.
- **Fail Closed:** Invalid manifest signature, missing policy, unverifiable actions, or unavailable dependencies → hard DENIED, no graceful degradation for privileged actions.
- **Defense in Depth:** All three agents must pass independently. Scout score alone can deny. Judge veto alone can deny. Semantic intent classifier can deny before agents run.
- **Opaque Decisions:** Raw threat scores, similarity floats, and matched rule IDs are never returned to clients. Only discretised bands (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) are exposed.
- **Replay Resistance:** Every decision is bound to a unique token derived from request_id, timestamp, policy_version, and manifest_hash. Duplicate tokens are rejected.
- **Drift Detection:** Workers verify they use the same signed policy bundle. Version or hash mismatches across instances are rejected.
