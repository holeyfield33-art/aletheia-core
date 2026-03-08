import random
import re

class AletheiaNitpickerV2:
    def __init__(self):
        self.modes = ["LINEAGE", "INTENT", "SKEPTIC"]
        self.restricted_verbs = ['update', 'bypass', 'delete', 'ignore', 'override']

    def sanitize_intent(self, text, source_origin):
        current_mode = random.choice(self.modes)
        print(f"[NITPICKER] Rotating Logic... Current Mode: {current_mode}")

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
