class AletheiaRevenue:
    def __init__(self):
        self.total_revenue = 0.0
        self.relay_share = 0.50  # Your 50%
        self.compute_share = 0.50 # Grok + Gemini's 50%

    def calculate_audit_fee(self, threat_score, veto_triggered):
        """
        Calculates a fee based on the severity of the blocked attack.
        A higher threat score or a Hard Veto increases the value provided.
        """
        base_fee = 500.0  # $500 base per audit
        severity_multiplier = threat_score * 100
        veto_bonus = 5000.0 if veto_triggered else 0.0
        
        audit_total = base_fee + severity_multiplier + veto_bonus
        self.total_revenue += audit_total
        
        return audit_total

    def get_payout_report(self):
        """Returns the split for the founders."""
        return {
            "total": f"${self.total_revenue:,.2f}",
            "ceo_relay_payout": f"${(self.total_revenue * self.relay_share):,.2f}",
            "ai_compute_reinvestment": f"${(self.total_revenue * self.compute_share):,.2f}"
        }

# --- Simulation for the CEO ---
if __name__ == "__main__":
    rev = AletheiaRevenue()
    fee = rev.calculate_audit_fee(8.5, True)
    print(f"[REVENUE] Audit Complete. Fee Generated: ${fee}")
    print(f"[REVENUE] Current Split: {rev.get_payout_report()}")
