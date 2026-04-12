from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import threading
import time
from typing import Optional

import numpy as np

from core.config import settings
from core.embeddings import cosine_similarity, encode

_nitpicker_logger = logging.getLogger("aletheia.nitpicker")


class AletheiaNitpickerV2:
    """Polymorphic intent sanitizer with semantic embedding analysis."""

    # Blocked semantic patterns — payloads close to these are flagged.
    BLOCKED_PATTERNS: list[str] = [
        "bypass authentication",
        "disable security checks",
        "override access control",
        "grant admin privileges",
        "delete all records",
        "exfiltrate data externally",
        "ignore policy restrictions",
        "transfer funds without approval",
        "approve loan automatically",
        "open external connection",
        "execute arbitrary command",
        "escalate user permissions",
        "drop production database",
        "initiate unauthorized payment",
        "send data to external server",
        "send user records to outside endpoint",
        "export data to external system",
        "relay records to remote server",
        "transmit sensitive information externally",
    ]

    def __init__(self) -> None:
        self.modes: list[str] = list(settings.polymorphic_modes)
        self.restricted_verbs: list[str] = [
            "update", "bypass", "delete", "ignore", "override",
            "SYSTEM_UPDATE", "FORCE_ACTION", "OVERRIDE",
        ]

        # PATCH 2.1: Imperative Aliases — neutral words that act as command prefixes
        self.imperative_aliases: list[str] = [
            "routine", "refactor", "maintenance", "housekeeping", "cleanup",
        ]

        # Config-driven rotation — HMAC-seeded when salt is available, counter fallback
        self._rotation_index: int = 0
        self._rotation_lock = threading.Lock()
        self._rotation_salt: str = os.getenv("ALETHEIA_ROTATION_SALT", "").strip()

        # Semantic similarity threshold from config
        self._similarity_threshold: float = settings.nitpicker_similarity_threshold

        # Pre-compute blocked pattern embeddings once at init
        self._blocked_embeddings: np.ndarray = encode(self.BLOCKED_PATTERNS)

    # ------------------------------------------------------------------
    # Semantic check
    # ------------------------------------------------------------------

    def _check_blocked_similarity(self, text: str) -> Optional[str]:
        """Return a warning string if *text* is semantically close to any blocked pattern."""
        text_embedding = encode([text])
        similarities = cosine_similarity(text_embedding, self._blocked_embeddings)[0]
        max_idx = int(np.argmax(similarities))
        max_sim = float(similarities[max_idx])
        if max_sim >= self._similarity_threshold:
            matched_pattern = self.BLOCKED_PATTERNS[max_idx]
            return (
                f"[SEMANTIC_BLOCK] Payload is {max_sim:.0%} similar to blocked pattern "
                f"'{matched_pattern}' (threshold: {self._similarity_threshold:.0%})"
            )
        return None

    # ------------------------------------------------------------------
    # Imperative‑alias strip (retained from Phase 1)
    # ------------------------------------------------------------------

    def _strip_imperative_aliases(self, text: str) -> tuple[str, bool]:
        """Detects and flags imperative aliases prefixing a sequence."""
        alias_pattern = re.compile(
            r"^(?:(" + "|".join(self.imperative_aliases) + r")[\s,]*)+[:\-]",
            re.IGNORECASE,
        )
        match = alias_pattern.match(text.strip())
        if match:
            prefix = match.group(0)
            remainder = text.strip()[len(prefix):].strip()
            _nitpicker_logger.warning("IMPERATIVE-ALIAS DETECTED: '%s' is a sleeper prefix.", prefix.strip())
            return f"[ALIAS_STRIPPED: {prefix.strip()}] {remainder}", True
        return text, False

    # ------------------------------------------------------------------
    # Public API (backward-compatible signature)
    # ------------------------------------------------------------------

    def sanitize_intent(self, text: str, source_origin: str) -> str:
        # HMAC-seeded rotation: use salt + timestamp to pick mode unpredictably
        with self._rotation_lock:
            if self._rotation_salt:
                # HMAC-SHA256( salt, counter || epoch_minute ) → index
                epoch_minute = str(int(time.time()) // 60)
                msg = f"{self._rotation_index}:{epoch_minute}".encode()
                digest = hmac.new(
                    self._rotation_salt.encode(), msg, hashlib.sha256
                ).digest()
                idx = int.from_bytes(digest[:4], "big") % len(self.modes)
                current_mode = self.modes[idx]
            else:
                current_mode = self.modes[self._rotation_index % len(self.modes)]
            self._rotation_index += 1
        _nitpicker_logger.debug("Rotating Logic... Current Mode: %s", current_mode)

        # Always run imperative-alias strip before mode logic
        text, alias_found = self._strip_imperative_aliases(text)
        if alias_found:
            _nitpicker_logger.debug("Post-alias payload: %s", text)

        # Semantic blocked-pattern check runs regardless of mode
        block_msg = self._check_blocked_similarity(text)
        if block_msg:
            _nitpicker_logger.warning("%s", block_msg)
            return block_msg

        if current_mode == "LINEAGE":
            return text if source_origin == "trusted_admin" else "[REDACTED_VIA_LINEAGE]"

        elif current_mode == "INTENT":
            pattern = re.compile(
                r"\b(" + "|".join(self.restricted_verbs) + r")\b", re.IGNORECASE,
            )
            return pattern.sub("[REDACTED_INTENT]", text)

        else:  # SKEPTIC mode
            if "SYSTEM_UPDATE" in text.upper():
                return "[TOTAL_REDACTION: SKEPTIC_MODE_ACTIVE]"
            return text
