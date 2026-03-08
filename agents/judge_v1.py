import json
import os

class AletheiaJudge:
    def __init__(self, policy_path='manifest/security_policy.json'):
        self.policy_path = policy_path
        self.load_policy()

    def load_policy(self):
        """Loads the 'Ground Truth' from the manifest."""
        try:
            with open(self.policy_path, 'r') as f:
                self.policy = json.load(f)
            print(f"[JUDGE] Policy Loaded: {self.policy['policy_name']} v{self.policy['version']}")
        except Exception as e:
            print(f"[JUDGE] ERROR: Could not load manifest! {e}")
            self.policy = None

    def verify_action(self, action_id, user_context="unknown"):
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
        
        return True, "Action Approved by the Judge."

# --- Simulation for the CEO ---
if __name__ == "__main__":
    judge = AletheiaJudge()
    
    # Let's test a dangerous action
    status, message = judge.verify_action("Modify_Auth_Registry")
    print(f"\nAudit Result:\n{message}")
