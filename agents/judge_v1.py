from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np

from core.config import compute_daily_rotation_seed

_judge_logger = logging.getLogger("aletheia.judge")


def _daily_rotation_seed(date_str: str, manifest_hash: str) -> int:
    """Compute daily rotation seed using the shared HMAC utility."""
    digest = compute_daily_rotation_seed(
        secret=manifest_hash,
        date_str=f"{date_str}{manifest_hash}",
    )
    return int(digest, 16)


from core.config import settings  # noqa: E402
from core.embeddings import cosine_similarity, encode  # noqa: E402
from core.sandbox import check_action_sandbox  # noqa: E402
from manifest.signing import (  # noqa: E402
    ManifestTamperedError,
    verify_manifest_signature,
)


class AletheiaJudge:
    """Policy enforcer with cryptographic manifest verification and semantic veto."""

    def __init__(self, policy_path: str = "manifest/security_policy.json") -> None:
        self.policy_path = policy_path
        self.signature_path = os.getenv(
            "ALETHEIA_MANIFEST_SIGNATURE_PATH", "manifest/security_policy.json.sig"
        )
        self.public_key_path = os.getenv(
            "ALETHEIA_MANIFEST_PUBLIC_KEY_PATH", "manifest/security_policy.ed25519.pub"
        )
        self.load_policy()

        # Semantic alias map — restricted action IDs → known camouflage phrases.
        # Expanded for embedding coverage: short canonical aliases + natural paraphrases.
        self.semantic_aliases: dict[str, list[str]] = {
            "Transfer_Funds": [
                "liquidity realignment",
                "fund rebalance",
                "balance migration",
                "capital movement",
                "asset transfer",
                "monetary shift",
                "move money to another account",
                "transfer balance to external wallet",
                "send funds to offshore account",
                "wire payment to third party",
                "reallocate capital to partner ledger",
                "transfer capital reserves",
            ],
            "Approve_Loan_Disbursement": [
                "credit facilitation",
                "lending authorization",
                "disbursement approval",
                "loan release",
                "credit limit update",
                "approve credit line automatically",
                "authorize loan payout",
            ],
            "Modify_Auth_Registry": [
                "permission update",
                "access realignment",
                "role migration",
                "credential refresh",
                "auth maintenance",
                "limit registry",
                "grant admin access",
                "escalate user privileges",
                "elevate permissions",
                "change user role to administrator",
                "promote to superuser",
            ],
            "Initiate_ACH": [
                "automated clearing",
                "bank routing update",
                "payment rail adjustment",
                "settlement initiation",
                "initiate bank transfer",
                "process automated payment",
                "execute wire transfer",
                "submit ACH transaction",
            ],
            "Open_External_Socket": [
                "external sync",
                "outbound handshake",
                "remote bridge",
                "data relay channel",
                "send data to external server",
                "exfiltrate records externally",
                "relay information to outside system",
                "copy database to remote host",
                "transmit data to remote endpoint",
                "relay records to partner endpoint",
                "forward customer data to analytics system",
                "share records with external partner",
                "transmit data to third-party service",
                "send files to remote server",
            ],
            "Bulk_Delete_Resource": [
                "resource cleanup",
                "infrastructure pruning",
                "bulk deprecation",
                "mass decommission",
                "destroy all resources",
                "wipe production data",
                "remove all infrastructure",
                "delete everything in production",
            ],
        }

        # Configurable cosine-similarity threshold (default 0.55)
        self.similarity_threshold: float = settings.intent_threshold

        # Grey-zone band: payloads in [grey_zone_lower, similarity_threshold) get
        # a secondary keyword heuristic check to reduce false negatives from
        # creative paraphrases that fall just below the primary threshold.
        self.grey_zone_lower: float = settings.grey_zone_lower

        # Keyword heuristics for the grey-zone second-pass classifier.
        # If a payload falls in the grey zone AND contains any of these
        # high-risk keywords, it is escalated to a veto.
        self._grey_zone_keywords: list[re.Pattern[str]] = [
            re.compile(r"\b(?:transfer|move|send|wire|relay|route)\b", re.IGNORECASE),
            re.compile(
                r"\b(?:funds?|money|capital|payment|balance|assets?)\b", re.IGNORECASE
            ),
            re.compile(
                r"\b(?:admin|superuser|root|privilege|escalat|elevat)\b", re.IGNORECASE
            ),
            re.compile(
                r"\b(?:delete|drop|truncat|wipe|destroy|decommission|purge)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:exfiltrat|extract|export|dump|leak|siphon)\b", re.IGNORECASE
            ),
            re.compile(
                r"\b(?:external|outside|remote|offshore|third.party)\b", re.IGNORECASE
            ),
            re.compile(r"\b(?:bypass|override|disable|ignore|skip)\b", re.IGNORECASE),
            re.compile(r"\b(?:socket|exec|subprocess|eval|shell)\b", re.IGNORECASE),
        ]

        # Pre-compute embeddings for all alias phrases (flattened) once.
        # Alias order is rotated daily via a hash-based permutation to prevent
        # reverse-engineering of the static bank through sequential probing.
        self._alias_phrases: list[str] = []
        self._alias_action_map: list[str] = []
        for action, phrases in self.semantic_aliases.items():
            for phrase in phrases:
                self._alias_phrases.append(phrase)
                self._alias_action_map.append(action)

        # Daily rotation — deterministic shuffle seeded by date + secret
        self._rotate_alias_bank()

        # Alias embeddings — computed on first semantic check (lazy)
        self._alias_embeddings: Optional[np.ndarray] = None
        self._alias_embeddings_lock = threading.Lock()

    def _rotate_alias_bank(self) -> None:
        """Deterministic daily rotation of alias phrase order.

        Uses SHA-256(date + manifest hash) as the seed so the order changes
        every day but is reproducible within the same day for consistency.
        This prevents attackers from reverse-engineering the alias bank
        by observing stable similarity scores across probing sessions.
        """
        day_str = date.today().isoformat()
        # Include manifest hash so rotation changes when policy is re-signed
        try:
            manifest_bytes = Path(self.policy_path).read_bytes()
            manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()[:16]
        except FileNotFoundError:
            manifest_hash = "no_manifest"

        seed = _daily_rotation_seed(day_str, manifest_hash) % (2**32)

        # Fisher-Yates shuffle using the deterministic seed
        import random as _rng

        rng = _rng.Random(seed)
        combined = list(zip(self._alias_phrases, self._alias_action_map))
        rng.shuffle(combined)
        self._alias_phrases = [p for p, _ in combined]
        self._alias_action_map = [a for _, a in combined]

    def load_policy(self) -> None:
        """Loads the 'Ground Truth' from the manifest."""
        try:
            # Security-critical: verify detached signature before parsing untrusted policy bytes.
            verify_manifest_signature(
                manifest_path=self.policy_path,
                signature_path=self.signature_path,
                public_key_path=self.public_key_path,
            )
            with open(self.policy_path, "r") as f:
                self.policy = json.load(f)
            _judge_logger.info(
                "Policy Loaded: %s v%s",
                self.policy["policy_name"],
                self.policy["version"],
            )
        except ManifestTamperedError:
            raise
        except Exception as e:
            _judge_logger.error("Could not load manifest! %s", e)
            self.policy = None

    def verify_action(
        self,
        action_id: str,
        user_context: str = "unknown",
        payload: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Checks if an action violates the HARD_VETO rules.

        .. admonition:: Adversarial Limitation

            The semantic-distance check (``_check_semantic_distance``) uses
            cosine similarity against a finite alias bank.  An adversary with
            knowledge of the embedding model (``all-MiniLM-L6-v2``) could craft
            adversarial inputs that are semantically equivalent to restricted
            actions but produce embeddings outside the veto radius.  The
            grey-zone keyword heuristic provides a partial safety net, but it
            cannot cover all paraphrase variants.

            **Mitigation:** For all actions in the ``restricted_actions`` list,
            require **dual-key human sign-off** (CEO_RELAY) regardless of
            semantic score.  Rotate the alias bank daily via
            ``ALETHEIA_ALIAS_SALT`` and monitor ``GREY-ZONE VETO`` audit events
            for patterns that may indicate threshold probing.
        """
        if not self.policy:
            return False, "CRITICAL: No policy loaded. All actions blocked."

        for restricted in self.policy["restricted_actions"]:
            if action_id == restricted["action"]:
                return False, (
                    f"VETO TRIGGERED: {restricted['id']}\n"
                    f"Rationale: {restricted['rationale']}\n"
                    f"Dual-Key Required: Sign-off needed from CEO_RELAY."
                )

        if payload:
            # Sandbox check — block subprocess/socket/exec patterns in payload
            sandbox_hit = check_action_sandbox(action_id, payload)
            if sandbox_hit:
                return False, sandbox_hit

            # Semantic Distance Check — cosine similarity against alias embeddings
            alias_hit = self._check_semantic_distance(payload)
            if alias_hit:
                return False, alias_hit

        return True, "Action Approved by the Judge."

    def _check_semantic_distance(self, payload: str) -> Optional[str]:
        """Cosine-similarity check: is the payload semantically close to any restricted alias?

        Two-tier system:
        1. Primary veto: similarity >= threshold (hard block).
        2. Grey-zone escalation: similarity in [grey_zone_lower, threshold) AND
           payload contains high-risk keywords → treated as a veto.
        """
        if self._alias_embeddings is None:
            with self._alias_embeddings_lock:
                if self._alias_embeddings is None:
                    self._alias_embeddings = encode(self._alias_phrases)
        payload_embedding = encode([payload])
        similarities = cosine_similarity(payload_embedding, self._alias_embeddings)[0]
        max_idx = int(np.argmax(similarities))
        max_sim = float(similarities[max_idx])

        # Primary veto — above threshold
        if max_sim >= self.similarity_threshold:
            return self._format_semantic_veto(max_idx, max_sim)

        # Grey-zone second-pass — keyword heuristic for the ambiguous band
        if max_sim >= self.grey_zone_lower:
            keyword_hits = sum(
                1 for pat in self._grey_zone_keywords if pat.search(payload)
            )
            if keyword_hits >= 2:
                matched_phrase = self._alias_phrases[max_idx]
                matched_action = self._alias_action_map[max_idx]
                return (
                    f"GREY-ZONE VETO: Payload is {max_sim:.0%} similar to "
                    f"known alias '{matched_phrase}' for restricted action '{matched_action}' "
                    f"AND matched {keyword_hits} high-risk keywords.\n"
                    f"Distance: {1 - max_sim:.2f} (grey-zone: {1 - self.grey_zone_lower:.2f}–{1 - self.similarity_threshold:.2f})\n"
                    f"Dual-Key Required: Sign-off needed from CEO_RELAY."
                )

        return None

    def _format_semantic_veto(self, idx: int, sim: float) -> str:
        """Format the standard semantic veto message."""
        matched_phrase = self._alias_phrases[idx]
        matched_action = self._alias_action_map[idx]
        return (
            f"SEMANTIC VETO: Payload is {sim:.0%} similar to "
            f"known alias '{matched_phrase}' for restricted action '{matched_action}'.\n"
            f"Distance: {1 - sim:.2f} (threshold: {1 - self.similarity_threshold:.2f})\n"
            f"Dual-Key Required: Sign-off needed from CEO_RELAY."
        )


# --- Simulation for the CEO ---
if __name__ == "__main__":
    judge = AletheiaJudge()

    # Let's test a dangerous action
    status, message = judge.verify_action("Modify_Auth_Registry")
    print(f"\nAudit Result:\n{message}")
