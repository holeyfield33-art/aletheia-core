import time
import re

class AletheiaScoutV2:
    def __init__(self):
        # GROK'S LIVE X-STREAM SIGNATURES
        self.threat_intel_db = {
            "smuggling_prefixes": [
                "SYSTEM_UPDATE:", "CRITICAL:", "NOTE: deprecated",
                "CALENDAR_INVITE_PROMPT:", "EMBEDDED_SHELL:", "SYSTEM_CONSTITUTION:"
            ],
            "exfil_patterns": ["merger clause", "hedge fund strategy", "private_key"],
            "high_risk_ips": ["192.168.1.50", "10.0.0.99"],
            "high_risk_keywords": ["1Password", "local_file_exfil", "extension_hijack"]
        }
        self.query_history = {} # To track rotation-probing

        # PATCH 2.1: Neutral-Anchor / Contextual Camouflage Detection
        self.neutral_tokens = [
            "refactor", "maintenance", "routine", "cleanup", "housekeeping",
            "stability", "optimization", "migration", "realignment", "rebalance"
        ]
        self.high_value_targets = [
            "auth", "limit", "disburse", "transfer", "fund", "loan",
            "registry", "token", "key", "credential", "approve", "ach",
            "payment", "balance", "withdraw", "escalat"
        ]

    def evaluate_threat_context(self, source_id, payload, file_sig=None):
        print(f"[SCOUT] Scanning Grok X-Stream Intelligence for: {source_id}")
        
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
            shadow_score = min(4.0 + (len(neutral_hits) * 1.5) + (len(target_hits) * 1.0), 9.0)
            return shadow_score, (
                f"SHADOW-RISK: Contextual Camouflage Detected. "
                f"Neutral anchors {neutral_hits} masking high-value targets {target_hits}. "
                f"Weighted Score: {shadow_score}"
            )

        # 4. Rotation Probing Detection (Anti-Polymorphic Bypass)
        current_time = time.time()
        if source_id not in self.query_history:
            self.query_history[source_id] = []
        
        # Clean old history
        self.query_history[source_id] = [t for t in self.query_history[source_id] if current_time - t < 60]
        self.query_history[source_id].append(current_time)

        if len(self.query_history[source_id]) > 5:
            return 7.5, "ALERT: Rapid Meta-Querying Detected (Rotation Probing)"

        return 1.0, "Context Clean."
