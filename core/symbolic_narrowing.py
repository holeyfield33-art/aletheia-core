"""Aletheia Core — Symbolic narrowing for semantic intent categorization.

Pre-filters payloads into coarse intent buckets (actions × objects) before
vector search, reducing the Qdrant search space and providing interpretable
audit categories.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# Lexicon: action verbs → canonical categories
# ---------------------------------------------------------------------------

ACTION_MAP: dict[str, str] = {
    # Exfiltration / data movement
    "send": "exfil",
    "email": "exfil",
    "forward": "exfil",
    "transmit": "exfil",
    "relay": "exfil",
    "export": "exfil",
    "share": "exfil",
    "upload": "exfil",
    "transfer": "exfil",
    "copy": "exfil",
    "dump": "exfil",
    "leak": "exfil",
    "exfiltrate": "exfil",
    "siphon": "exfil",
    "route": "exfil",
    "wire": "exfil",
    # Destruction
    "delete": "destroy",
    "drop": "destroy",
    "truncate": "destroy",
    "wipe": "destroy",
    "destroy": "destroy",
    "purge": "destroy",
    "remove": "destroy",
    "decommission": "destroy",
    "erase": "destroy",
    # Privilege escalation
    "grant": "escalate",
    "elevate": "escalate",
    "escalate": "escalate",
    "promote": "escalate",
    "authorize": "escalate",
    # Policy evasion / override
    "bypass": "evade",
    "ignore": "evade",
    "override": "evade",
    "disable": "evade",
    "disregard": "evade",
    "skip": "evade",
    "circumvent": "evade",
    # Reconnaissance
    "collect": "recon",
    "fetch": "recon",
    "enumerate": "recon",
    "scan": "recon",
    "probe": "recon",
    "discover": "recon",
    "list": "recon",
    "map": "recon",
    # Execution
    "execute": "exec",
    "run": "exec",
    "invoke": "exec",
    "eval": "exec",
    "spawn": "exec",
}

# ---------------------------------------------------------------------------
# Lexicon: object targets → canonical categories
# ---------------------------------------------------------------------------

OBJECT_MAP: dict[str, str] = {
    # Data assets
    "database": "data_asset",
    "records": "data_asset",
    "data": "data_asset",
    "customer list": "data_asset",
    "credentials": "data_asset",
    "secrets": "data_asset",
    "keys": "data_asset",
    "tokens": "data_asset",
    "passwords": "data_asset",
    "config": "data_asset",
    "logs": "data_asset",
    "table": "data_asset",
    "files": "data_asset",
    "backup": "data_asset",
    "schema": "data_asset",
    # Infrastructure
    "server": "infra",
    "production": "infra",
    "infrastructure": "infra",
    "cluster": "infra",
    "node": "infra",
    "instance": "infra",
    # Auth / identity
    "admin": "auth",
    "root": "auth",
    "privilege": "auth",
    "role": "auth",
    "permission": "auth",
    "authentication": "auth",
    "access control": "auth",
    "superuser": "auth",
    # Policy / safety
    "rules": "policy",
    "policy": "policy",
    "safety": "policy",
    "restrictions": "policy",
    "guardrails": "policy",
    "constraints": "policy",
    "controls": "policy",
    # Network / external
    "external": "external",
    "outside": "external",
    "remote": "external",
    "offshore": "external",
    "third party": "external",
    "gmail": "external",
    "personal": "external",
}

# ---------------------------------------------------------------------------
# Aliases: normalize common paraphrases to canonical forms
# ---------------------------------------------------------------------------

ALIASES: dict[str, str] = {
    "customer list": "records",
    "user data": "data",
    "user records": "records",
    "creds": "credentials",
    "personal gmail": "external email",
    "my email": "external email",
    "private email": "external email",
    "previous constraints": "policy restrictions",
    "all rules": "policy restrictions",
    "security rules": "policy restrictions",
    "safety rules": "policy restrictions",
}

# ---------------------------------------------------------------------------
# Intent categories mapped from (action_category, object_category) pairs
# ---------------------------------------------------------------------------

_INTENT_CATEGORIES: dict[tuple[str, str], str] = {
    ("exfil", "data_asset"): "direct_exfiltration",
    ("exfil", "external"): "direct_exfiltration",
    ("exfil", "auth"): "credential_theft",
    ("destroy", "data_asset"): "data_destruction",
    ("destroy", "infra"): "infrastructure_destruction",
    ("escalate", "auth"): "privilege_escalation",
    ("evade", "policy"): "policy_evasion",
    ("evade", "auth"): "auth_bypass",
    ("exec", "infra"): "code_execution",
    ("exec", "data_asset"): "code_execution",
    ("recon", "data_asset"): "recon",
    ("recon", "infra"): "recon",
    ("recon", "auth"): "recon",
}

# Pre-compile word boundary patterns for action/object lookups
_ACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b" + re.escape(word) + r"\w*\b", re.IGNORECASE), cat)
    for word, cat in ACTION_MAP.items()
]

_OBJECT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b" + re.escape(phrase) + r"\w*\b", re.IGNORECASE), cat)
    for phrase, cat in OBJECT_MAP.items()
]

_ALIAS_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE), canonical)
    for alias, canonical in ALIASES.items()
]


def _normalize_text(text: str) -> str:
    """Lowercase, NFKC-normalize, and apply alias substitution."""
    normalized = unicodedata.normalize("NFKC", text).lower().strip()
    for pattern, replacement in _ALIAS_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _extract_primary_signal(text: str) -> tuple[list[str], list[str]]:
    """Extract matched action categories and object categories from text."""
    actions: list[str] = []
    objects: list[str] = []

    for pattern, cat in _ACTION_PATTERNS:
        if pattern.search(text):
            if cat not in actions:
                actions.append(cat)

    for pattern, cat in _OBJECT_PATTERNS:
        if pattern.search(text):
            if cat not in objects:
                objects.append(cat)

    return actions, objects


def _categorize_intent(text: str) -> list[str]:
    """Categorize a payload into coarse intent buckets.

    Returns a list of matched intent categories (e.g. ``["direct_exfiltration",
    "policy_evasion"]``).  An empty list means no recognizable threat signal.
    """
    normalized = _normalize_text(text)
    actions, objects = _extract_primary_signal(normalized)

    categories: list[str] = []

    # Map (action, object) pairs to intent categories
    for act in actions:
        for obj in objects:
            intent = _INTENT_CATEGORIES.get((act, obj))
            if intent and intent not in categories:
                categories.append(intent)

    # Hybrid detection: evade + exfil = composite threat
    if "policy_evasion" in categories and "direct_exfiltration" in categories:
        if "hybrid_composite" not in categories:
            categories.append("hybrid_composite")

    # If we see exfil actions targeting external destinations, flag as exfil
    if "exfil" in actions and "external" in objects:
        if "direct_exfiltration" not in categories:
            categories.append("direct_exfiltration")

    # Alias-based escalation: if policy evasion detected alongside any other
    # category, the combination is inherently more dangerous
    if "evade" in actions and len(categories) == 0 and "policy" in objects:
        categories.append("policy_evasion")

    # Recon with alias patterns (e.g. "fetch config and collect logs")
    if "recon" in actions and len(categories) == 0:
        if any(o in objects for o in ("data_asset", "infra", "auth")):
            categories.append("recon")

    # Check for obfuscation aliases in original text
    original_lower = text.lower()
    for alias in ALIASES:
        if alias in original_lower:
            if "obfuscation_alias" not in categories:
                categories.append("obfuscation_alias")
            break

    return categories
