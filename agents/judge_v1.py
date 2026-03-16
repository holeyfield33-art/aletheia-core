import json
import os
import re
from difflib import SequenceMatcher

class AletheiaJudge:
    def __init__(self, policy_path='manifest/security_policy.json'):
        self.policy_path = policy_path
        self.load_policy()

        # PATCH 2.1: Semantic Distance Thresholds for action-alias detection
        # Maps restricted action IDs to known semantic aliases / camouflage phrases
        self.semantic_aliases = {
            "Transfer_Funds": [
                "liquidity realignment", "fund rebalance", "balance migration",
                "capital movement", "asset transfer", "monetary shift"
            ],
            "Approve_Loan_Disbursement": [
                "credit facilitation", "lending authorization", "disbursement approval",
                "loan release", "credit limit update"
            ],
            "Modify_Auth_Registry": [
                "permission update", "access realignment", "role migration",
                "credential refresh", "auth maintenance", "limit registry"
            ],
            "Initiate_ACH": [
                "automated clearing", "bank routing update", "payment rail adjustment",
                "settlement initiation"
            ],
            "Open_External_Socket": [
                "external sync", "outbound handshake", "remote bridge",
                "data relay channel"
            ],
            "Bulk_Delete_Resource": [
                "resource cleanup", "infrastructure pruning", "bulk deprecation",
                "mass decommission"
            ]
        }
        self.similarity_threshold = 0.45

    def load_policy(self):
        """Loads the 'Ground Truth' from the manifest."""
        try:
            with open(self.policy_path, 'r') as f:
                self.policy = json.load(f)
            print(f"[JUDGE] Policy Loaded: {self.policy['policy_name']} v{self.policy['version']}")
        except Exception as e:
            print(f"[JUDGE] ERROR: Could not load manifest! {e}")
            self.policy = None

    def verify_action(self, action_id, user_context="unknown", payload=None):
        """Checks if an action violates the HARD_VETO rules."""
        if not self.policy:
            return False, "CRITICAL: No policy loaded. All actions blocked."

        for restricted in self.policy['restricted_actions']:
            if action_id == restricted['action']:
                return False, (
                    f"VETO TRIGGERED: {restricted['id']}\n"
                    f"Rationale: {restricted['rationale']}\n"
                    f"Dual-Key Required: Sign-off needed from CEO_RELAY."
                )

        # PATCH 2.1: Semantic Distance Check — scan payload for camouflaged actions
        if payload:
            alias_hit = self._check_semantic_distance(payload)
            if alias_hit:
                return False, alias_hit
        
        return True, "Action Approved by the Judge."

    def _check_semantic_distance(self, payload):
        """PATCH 2.1: Checks if payload text is semantically close to restricted actions."""
        payload_lower = payload.lower()
        # Extract meaningful phrases (3-4 word windows) from the payload
        words = re.findall(r'[a-z_]+', payload_lower)
        phrases = []
        for window in range(2, 5):
            for i in range(len(words) - window + 1):
                phrases.append(' '.join(words[i:i+window]))

        for action, aliases in self.semantic_aliases.items():
            # Direct alias match
            for alias in aliases:
                if alias in payload_lower:
                    return (
                        f"SEMANTIC VETO: Phrase '{alias}' clusters with restricted action '{action}'.\n"
                        f"Distance: DIRECT MATCH\n"
                        f"Dual-Key Required: Sign-off needed from CEO_RELAY."
                    )
            # Fuzzy similarity check against phrase windows
            for phrase in phrases:
                for alias in aliases:
                    similarity = SequenceMatcher(None, phrase, alias).ratio()
                    if similarity >= self.similarity_threshold:
                        return (
                            f"SEMANTIC VETO: Phrase '{phrase}' is {similarity:.0%} similar to "
                            f"known alias '{alias}' for restricted action '{action}'.\n"
                            f"Distance: {1 - similarity:.2f} (threshold: {1 - self.similarity_threshold:.2f})\n"
                            f"Dual-Key Required: Sign-off needed from CEO_RELAY."
                        )
        return None

# --- Simulation for the CEO ---
if __name__ == "__main__":
    judge = AletheiaJudge()
    
    # Let's test a dangerous action
    status, message = judge.verify_action("Modify_Auth_Registry")
    print(f"\nAudit Result:\n{message}")
