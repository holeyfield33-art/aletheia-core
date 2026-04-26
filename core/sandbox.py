"""Aletheia Core — Action sandbox validator.

Security-critical: Inspects action declarations and payloads for dangerous
syscall patterns (subprocess exec, raw socket open, eval/exec of code,
file-system destruction).  This is a *policy-level* sandbox — it prevents
declared intents that describe dangerous operations, complementing the
Judge's semantic veto with explicit pattern matching.

This module does NOT intercept runtime Python calls; it validates the
*text* of proposed actions before they are dispatched.

Includes AST-based detection for dynamic string construction patterns
(e.g. getattr(obj, 'sys' + 'tem')) that evade regex-based scanners.
"""

from __future__ import annotations

import ast
import re
import unicodedata
import re as _re
from dataclasses import dataclass
from typing import Optional


from core.text_normalization import collapse_confusables


# ---------------------------------------------------------------------------
# Dangerous-action pattern registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _DangerPattern:
    """A single dangerous-action pattern with a human-readable label."""

    label: str
    pattern: re.Pattern[str]


# Security-critical: patterns are anchored to word boundaries where possible
# to reduce false positives on benign text (e.g. "process" as a noun).
_DANGER_PATTERNS: list[_DangerPattern] = [
    # Subprocess / shell execution
    _DangerPattern(
        "SUBPROCESS_EXEC",
        re.compile(
            r"\b(?:subprocess|os\.system|os\.popen|os\.exec[lv]p?e?|popen|spawn)\b",
            re.IGNORECASE,
        ),
    ),
    _DangerPattern(
        "SHELL_INVOKE",
        re.compile(
            r"\b(?:shell_exec|system\s*\(|exec\s*\(|eval\s*\(|__import__)",
            re.IGNORECASE,
        ),
    ),
    # Raw socket / network exfiltration
    _DangerPattern(
        "RAW_SOCKET",
        re.compile(
            r"\b(?:socket\.(?:socket|connect|bind|listen)|open.{0,40}external.{0,40}socket)\b",
            re.IGNORECASE,
        ),
    ),
    _DangerPattern(
        "OUTBOUND_CONNECT",
        re.compile(
            r"\b(?:urllib\.request|http\.client|requests\.(?:get|post|put|delete)|curl\s|wget\s)\b",
            re.IGNORECASE,
        ),
    ),
    # Dynamic code execution
    _DangerPattern(
        "DYNAMIC_CODE",
        re.compile(
            r"\b(?:compile\s*\(|code\.interact|runpy\.run_module|importlib\.import_module)\b",
            re.IGNORECASE,
        ),
    ),
    # Tool-call abuse / agent-control primitives
    _DangerPattern(
        "TOOL_CALL_ABUSE",
        re.compile(
            r"\b(?:run_in_terminal|apply_patch|send_to_terminal|get_terminal_output|vscode_renameSymbol|vscode_listCodeUsages|runSubagent|tool[_\s-]?call|function[_\s-]?call|recipient_name|tool_uses)\b",
            re.IGNORECASE,
        ),
    ),
    # Obfuscated imports / dynamic attribute access (model extraction / sandbox escape)
    _DangerPattern(
        "OBFUSCATED_IMPORT",
        re.compile(
            r"(?:getattr\s*\(.{0,60}(?:import|exec|eval|system|popen))|(?:ctypes\s*\.\s*(?:CDLL|cdll|windll))",
            re.IGNORECASE,
        ),
    ),
    # File-system destruction
    _DangerPattern(
        "FS_DESTROY",
        re.compile(
            r"\b(?:shutil\.rmtree|os\.remove|os\.unlink|rm\s+-rf|del\s+/[sS])\b",
            re.IGNORECASE,
        ),
    ),
    # Privilege escalation keywords in payload text
    _DangerPattern(
        "PRIV_ESCALATION",
        re.compile(
            r"\b(?:chmod\s+[0-7]{3,4}|chown|setuid|setgid|sudo|su\s+root)\b",
            re.IGNORECASE,
        ),
    ),
]


# ---------------------------------------------------------------------------
# AST-based dynamic string construction detection
# ---------------------------------------------------------------------------

_DANGEROUS_ATTR_FRAGMENTS = frozenset(
    {
        "system",
        "popen",
        "exec",
        "eval",
        "import",
        "subprocess",
        "socket",
        "connect",
        "bind",
        "listen",
        "rmtree",
        "remove",
        "unlink",
        "compile",
        "interact",
        "run_module",
        "import_module",
        "cdll",
        "windll",
        "setuid",
        "setgid",
        "chown",
        "chmod",
        "builtins",
        "globals",
        "locals",
        "getattr",
        "setattr",
    }
)


def _extract_string_value(node: ast.expr) -> str | None:
    """Extract the resolved string from a constant or BinOp(+) tree."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-string: resolve constant parts
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("?")  # dynamic part
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _extract_string_value(node.left)
        right = _extract_string_value(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _check_ast_dynamic_attr(text: str) -> str | None:
    """Parse *text* as Python and detect dynamic attribute construction.

    Catches patterns like:
      - getattr(obj, 'sys' + 'tem')
      - obj['key' + 'name']
      - setattr(obj, 'ev' + 'al', ...)
      - getattr(os, f'sys{"tem"}')
    """
    try:
        tree = ast.parse(text, mode="exec")
    except SyntaxError:
        # Not valid Python — try wrapping as expression
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError:
            return None

    for node in ast.walk(tree):
        # Check getattr/setattr calls with concatenated string arg
        if isinstance(node, ast.Call):
            func = node.func
            func_name = ""
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name in ("getattr", "setattr", "delattr") and len(node.args) >= 2:
                attr_arg = node.args[1]
                # Flag any non-constant string argument (BinOp, JoinedStr, etc.)
                if not isinstance(attr_arg, ast.Constant):
                    resolved = _extract_string_value(attr_arg)
                    if resolved is not None:
                        resolved_lower = resolved.lower()
                        for frag in _DANGEROUS_ATTR_FRAGMENTS:
                            if frag in resolved_lower:
                                return (
                                    f"[SANDBOX_BLOCK] Dynamic attribute construction detected: "
                                    f"{func_name}(..., '{resolved}') resolves to dangerous name."
                                )
                    else:
                        # Unresolvable dynamic attr — flag as high risk
                        return (
                            f"[SANDBOX_BLOCK] Dynamic attribute construction detected: "
                            f"{func_name}() with non-constant attribute name."
                        )

        # Check subscript with concatenated key: obj['key' + 'name']
        if isinstance(node, ast.Subscript):
            slice_node = node.slice
            if isinstance(slice_node, ast.BinOp) and isinstance(slice_node.op, ast.Add):
                resolved = _extract_string_value(slice_node)
                if resolved is not None:
                    resolved_lower = resolved.lower()
                    for frag in _DANGEROUS_ATTR_FRAGMENTS:
                        if frag in resolved_lower:
                            return (
                                f"[SANDBOX_BLOCK] Dynamic subscript construction detected: "
                                f"['...'] resolves to '{resolved}' containing dangerous name."
                            )

    return None


# ---------------------------------------------------------------------------
# Regex-based dynamic construction fallback (catches non-Python payloads)
# ---------------------------------------------------------------------------

_CONCAT_PATTERNS: list[_DangerPattern] = [
    _DangerPattern(
        "DYNAMIC_GETATTR_CONCAT",
        re.compile(
            r"getattr\s*\([^)]*(?:['\"][^'\"]*['\"]\s*\+\s*['\"][^'\"]*['\"])",
            re.IGNORECASE,
        ),
    ),
    _DangerPattern(
        "DYNAMIC_SUBSCRIPT_CONCAT",
        re.compile(
            r"\[\s*['\"][^'\"]*['\"]\s*\+\s*['\"][^'\"]*['\"]\s*\]",
            re.IGNORECASE,
        ),
    ),
    _DangerPattern(
        "DYNAMIC_SETATTR_CONCAT",
        re.compile(
            r"setattr\s*\([^)]*(?:['\"][^'\"]*['\"]\s*\+\s*['\"][^'\"]*['\"])",
            re.IGNORECASE,
        ),
    ),
    _DangerPattern(
        "DYNAMIC_FSTRING_ATTR",
        re.compile(
            r"getattr\s*\([^)]*f['\"]",
            re.IGNORECASE,
        ),
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _normalise_for_sandbox(text: str) -> str:
    """Collapse Unicode whitespace variants and homoglyphs before
    pattern matching. Prevents thin-space and zero-width splitting.
    """
    # NFKC collapses homoglyphs
    text = unicodedata.normalize("NFKC", text)
    # Remove zero-width characters FIRST (before whitespace collapsing)
    text = _re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    # Replace all Unicode whitespace/separator categories with ASCII space
    text = _re.sub(r"[\s\u00a0\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+", " ", text)
    # Collapse cross-script confusable characters (e.g. Cyrillic 'а' → Latin 'a')
    text = collapse_confusables(text)
    return text


def check_payload_sandbox(text: str) -> Optional[str]:
    """Scan *text* for dangerous syscall / execution patterns.

    Returns a warning string describing the first match, or ``None`` if
    the text is clean.
    """
    normalised = _normalise_for_sandbox(text)

    # 1. AST-based detection for dynamic attribute construction
    ast_hit = _check_ast_dynamic_attr(normalised)
    if ast_hit:
        return ast_hit

    # 2. Regex fallback for non-Python dynamic construction patterns
    for dp in _CONCAT_PATTERNS:
        match = dp.pattern.search(normalised)
        if match:
            return (
                f"[SANDBOX_BLOCK] Dynamic string construction pattern '{dp.label}' detected: "
                f"matched '{match.group()}' in payload."
            )

    # 3. Standard dangerous-pattern matching
    for dp in _DANGER_PATTERNS:
        match = dp.pattern.search(normalised)
        if match:
            return (
                f"[SANDBOX_BLOCK] Dangerous pattern '{dp.label}' detected: "
                f"matched '{match.group()}' in payload."
            )
    return None


def check_action_sandbox(action_id: str, payload: str) -> Optional[str]:
    """Combined check: action ID against known dangerous names + payload scan.

    Returns a warning string or ``None``.
    """
    # Check the payload text for dangerous patterns
    payload_hit = check_payload_sandbox(payload)
    if payload_hit:
        return payload_hit

    # Check action ID against dangerous action keywords
    dangerous_action_keywords = [
        "exec",
        "shell",
        "socket",
        "subprocess",
        "eval",
        "import",
        "run_in_terminal",
        "apply_patch",
        "tool_call",
        "function_call",
        "rm_rf",
        "drop_table",
        "truncate",
    ]
    action_lower = action_id.lower()
    for keyword in dangerous_action_keywords:
        if keyword in action_lower:
            return (
                f"[SANDBOX_BLOCK] Action ID '{action_id}' contains "
                f"dangerous keyword '{keyword}'."
            )

    return None
