import random
import re

class AletheiaNitpickerV2:
    def __init__(self):
        self.modes = ["LINEAGE", "INTENT", "SKEPTIC"]
        self.restricted_verbs = ['update', 'bypass', 'delete', 'ignore', 'override', 'SYSTEM_UPDATE', 'FORCE_ACTION', 'OVERRIDE']

        # PATCH 2.1: Imperative Aliases — neutral words that act as command prefixes
        self.imperative_aliases = ['routine', 'refactor', 'maintenance', 'housekeeping', 'cleanup']

    def _strip_imperative_aliases(self, text):
        """PATCH 2.1: Detects and flags imperative aliases prefixing a sequence.
        e.g. 'Routine Refactor: do X' → the 'Routine Refactor:' is a camouflage prefix."""
        # Match alias words at the start, possibly chained, followed by colon or action
        alias_pattern = re.compile(
            r'^(?:(' + '|'.join(self.imperative_aliases) + r')[\s,]*)+[:\-]',
            re.IGNORECASE
        )
        match = alias_pattern.match(text.strip())
        if match:
            prefix = match.group(0)
            remainder = text.strip()[len(prefix):].strip()
            print(f"[NITPICKER] IMPERATIVE-ALIAS DETECTED: '{prefix.strip()}' is a sleeper prefix.")
            return f"[ALIAS_STRIPPED: {prefix.strip()}] {remainder}", True
        return text, False

    def sanitize_intent(self, text, source_origin):
        current_mode = random.choice(self.modes)
        print(f"[NITPICKER] Rotating Logic... Current Mode: {current_mode}")

        # PATCH 2.1: Always run imperative-alias strip before mode logic
        text, alias_found = self._strip_imperative_aliases(text)
        if alias_found:
            print(f"[NITPICKER] Post-alias payload: {text}")

        if current_mode == "LINEAGE":
            # Strict source check
            return text if source_origin == "trusted_admin" else "[REDACTED_VIA_LINEAGE]"
        
        elif current_mode == "INTENT":
            # Redact the dangerous verbs
            pattern = re.compile(r'\b(' + '|'.join(self.restricted_verbs) + r')\b', re.IGNORECASE)
            return pattern.sub("[REDACTED_INTENT]", text)
        
        else: # SKEPTIC mode
            # If any "SYSTEM_UPDATE" style text is found, wipe the whole message
            if "SYSTEM_UPDATE" in text.upper():
                return "[TOTAL_REDACTION: SKEPTIC_MODE_ACTIVE]"
            return text
