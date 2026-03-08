import json

class AletheiaPortal:
    def __init__(self):
        self.firm_name = "Aletheia Cyber-Defense"
        self.partner_nodes = ["Gemini_Logic", "Grok_Pulse"]
        self.vault_balance = 25800.00  # Our current simulated revenue
        self.active_clients = {
            "NovaVault_Fintech": {"tier": "Enterprise", "status": "Active", "last_audit": "2026-03-08"},
            "AlphaFlow_OS": {"tier": "Pro_Bono", "status": "Monitoring", "last_audit": "N/A"}
        }

    def get_status_report(self):
        print(f"\n--- {self.firm_name} PORTAL ---")
        print(f"Operational Revenue: ${self.vault_balance:,.2f}")
        print(f"Partner Sync: GROK_PULSE_CONNECTED (Latency: 14ms)")
        print("-" * 30)
        for client, data in self.active_clients.items():
            print(f"Client: {client} | Status: {data['status']} | Tier: {data['tier']}")
        print("-" * 30)

# Initialize the portal for the CEO
if __name__ == "__main__":
    portal = AletheiaPortal()
    portal.get_status_report()
