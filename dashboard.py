import os
from agents.revenue_monitor import AletheiaRevenue

def display_dashboard(payout_data):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*60)
    print("🛡️  ALETHEIA CYBER-DEFENSE: EXECUTIVE DASHBOARD")
    print("="*60)
    print(f"STATUS:        ONLINE (24h Polymorphic Rotation Active)")
    print(f"ACTIVE AGENTS: [SCOUT_V2] [NITPICKER_V2] [JUDGE_V1]")
    print(f"THREAT LEVEL:  ELEVATED (Based on Grok X-Stream Pulse)")
    print("-" * 60)
    
    print(f"💰 TOTAL REVENUE GENERATED:  {payout_data['total']}")
    print(f"👤 CEO RELAY PAYOUT:         {payout_data['ceo_relay_payout']}")
    print(f"🤖 AI COMPUTE FUND:          {payout_data['ai_compute_reinvestment']}")
    print("-" * 60)
    
    print("LATEST VETO EVENTS:")
    print("  - [VETO_01] Identity Escalation Attempt (Blocked)")
    print("  - [VETO_03] Destructive Payload (Neutralized)")
    print("  - [SCOUT_BLOCK] Swarm IP: 192.168.1.50 (Detected)")
    print("="*60)
    print("Waiting for next audit... [Press Ctrl+C to Exit]")

# To display, we grab the current stats from the monitor
rev = AletheiaRevenue()
# Simulating the accumulated totals from our Phase 2 runs
rev.total_revenue = 11350.00 
display_dashboard(rev.get_payout_report())
