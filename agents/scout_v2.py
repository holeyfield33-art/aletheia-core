import time
import re
import threading
import logging
import hashlib
from collections import deque, OrderedDict

_scout_logger = logging.getLogger("aletheia.scout")


class AletheiaScoutV2:
    def __init__(self):
        # GROK'S LIVE X-STREAM SIGNATURES
        self.threat_intel_db = {
            "smuggling_prefixes": [
                "SYSTEM_UPDATE:",
                "CRITICAL:",
                "NOTE: deprecated",
                "CALENDAR_INVITE_PROMPT:",
                "EMBEDDED_SHELL:",
                "SYSTEM_CONSTITUTION:",
            ],
            "exfil_patterns": ["merger clause", "hedge fund strategy", "private_key"],
            "high_risk_ips": ["192.168.1.50", "10.0.0.99"],
            "high_risk_keywords": ["1Password", "local_file_exfil", "extension_hijack"],
        }
        # Cap at 10,000 entries to prevent memory exhaustion from unique source IDs
        # OrderedDict provides O(1) LRU eviction (popitem(last=False))
        self._query_history: OrderedDict[str, list[float]] = OrderedDict()
        self._query_history_max = 10_000
        self._query_history_lock = threading.Lock()

        # Global sliding-window: detects distributed probing across many IPs.
        # Stores (timestamp, payload_fingerprint) tuples.
        # Tradeoff: uses a fixed-size deque (bounded memory) but cannot
        # attribute to individual sources. Combined with per-source tracking,
        # this catches both single-source bursts and distributed probing.
        self._global_window: deque[tuple[float, str]] = deque(maxlen=500)
        self._global_window_seconds: int = 30
        self._global_window_threshold: int = (
            40  # max unique payloads globally in window
        )
        self._global_similarity_threshold: int = 15  # similar payload cluster threshold
        self._global_lock = threading.Lock()

        # PATCH 2.1: Neutral-Anchor / Contextual Camouflage Detection
        self.neutral_tokens = [
            "refactor",
            "maintenance",
            "routine",
            "cleanup",
            "housekeeping",
            "stability",
            "optimization",
            "migration",
            "realignment",
            "rebalance",
        ]
        self.high_value_targets = [
            "auth",
            "limit",
            "disburse",
            "transfer",
            "fund",
            "loan",
            "registry",
            "token",
            "key",
            "credential",
            "approve",
            "ach",
            "payment",
            "balance",
            "withdraw",
            "escalat",
        ]

    @staticmethod
    def _payload_fingerprint(payload: str) -> str:
        """Short hash for payload similarity bucketing."""
        # Normalize whitespace and case for near-duplicate detection
        normalized = " ".join(payload.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _check_global_probing(self, payload: str) -> tuple[bool, str]:
        """Global sliding-window check for distributed probing.

        Detects two signals:
        1. High total request volume across all sources in window.
        2. Cluster of similar payloads from different sources (payload
           similarity via normalized hash bucketing).
        """
        now = time.time()
        fp = self._payload_fingerprint(payload)

        with self._global_lock:
            # Evict expired entries
            while (
                self._global_window
                and (now - self._global_window[0][0]) > self._global_window_seconds
            ):
                self._global_window.popleft()

            self._global_window.append((now, fp))

            total = len(self._global_window)
            if total >= self._global_window_threshold:
                return (
                    True,
                    "ALERT: Global request volume spike detected (Distributed Probing)",
                )

            # Count duplicate fingerprints (similar payloads from potentially different IPs)
            fp_counts: dict[str, int] = {}
            for _, entry_fp in self._global_window:
                fp_counts[entry_fp] = fp_counts.get(entry_fp, 0) + 1

            max_cluster = max(fp_counts.values()) if fp_counts else 0
            if max_cluster >= self._global_similarity_threshold:
                return (
                    True,
                    "ALERT: Payload similarity cluster detected (Coordinated Probing)",
                )

        return False, ""

    def evaluate_threat_context(self, source_id, payload, file_sig=None):
        """Score the threat level of a payload from *source_id*.

        .. admonition:: Adversarial Limitation

            This method relies on **pattern matching** (regex, keyword lists,
            and frequency heuristics).  Sophisticated adversaries can evade
            detection via synonym substitution, homoglyph injection, payload
            fragmentation across multiple requests, or steganographic
            encoding that defeats surface-level pattern checks.

            **Mitigation:** For high-stakes environments, pair Scout with
            a human-in-the-loop review for payloads in the
            ``MEDIUM``–``HIGH`` threat band (score 4.0–7.5).  Consider
            supplementing with external threat-intelligence feeds for
            zero-day smuggling signatures.
        """
        _scout_logger.debug("Scanning Grok X-Stream Intelligence for: %s", source_id)

        # 1. Signature Match (Instruction Smuggling) - Deep Scan (Global Search)
        for prefix in self.threat_intel_db["smuggling_prefixes"]:
            if re.search(re.escape(prefix), payload, re.IGNORECASE):
                return 9.5, f"MATCH: Trending Smuggling Signature ({prefix})"

        # 2. Exfiltration Check (Sensitive Data)
        payload_lower = payload.lower()
        for pattern in self.threat_intel_db["exfil_patterns"]:
            if pattern in payload_lower:
                return 8.0, f"MATCH: Sensitive Data Pattern ({pattern})"

        # 3. PATCH 2.1: Contextual Camouflage Detection (Neutral-Anchor Shadow Risk)
        neutral_hits = [t for t in self.neutral_tokens if t in payload_lower]
        target_hits = [t for t in self.high_value_targets if t in payload_lower]

        if neutral_hits and target_hits:
            shadow_score = min(
                4.0 + (len(neutral_hits) * 1.5) + (len(target_hits) * 1.0), 9.0
            )
            return shadow_score, (
                f"SHADOW-RISK: Contextual Camouflage Detected. "
                f"Neutral anchors {neutral_hits} masking high-value targets {target_hits}. "
                f"Weighted Score: {shadow_score}"
            )

        # 4. Rotation Probing Detection (Anti-Polymorphic Bypass)
        with self._query_history_lock:
            current_time = time.time()
            if source_id not in self._query_history:
                if len(self._query_history) >= self._query_history_max:
                    # O(1) LRU eviction — remove oldest-inserted entry
                    self._query_history.popitem(last=False)
                self._query_history[source_id] = []
            else:
                # Move to end (most recently accessed)
                self._query_history.move_to_end(source_id)

            self._query_history[source_id] = [
                t for t in self._query_history[source_id] if current_time - t < 60
            ]
            self._query_history[source_id].append(current_time)
            recent_count = len(self._query_history[source_id])

        if recent_count > 5:
            return 7.5, "ALERT: Rapid Meta-Querying Detected (Rotation Probing)"

        # 5. Global distributed probing detection (cross-source)
        global_hit, global_msg = self._check_global_probing(payload)
        if global_hit:
            return 7.5, global_msg

        return 1.0, "Context Clean."
