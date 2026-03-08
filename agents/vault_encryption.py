import hashlib
import time

class AletheiaVault:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.transaction_history = []
        self.secret_salt = "ALETHEIA_2026_PROTOTYPE"

    def sign_transaction(self, amount, category):
        """Creates a cryptographic hash for the transaction."""
        timestamp = time.ctime()
        tx_string = f"{amount}{category}{timestamp}{self.secret_salt}"
        tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
        
        self.balance += amount
        self.transaction_history.append({
            "amount": amount,
            "category": category,
            "hash": tx_hash[:16], # Shorthand for the logs
            "time": timestamp
        })
        return tx_hash[:16]

    def get_audit_log(self):
        print(f"\n🔑 VAULT ENCRYPTED LEDGER - BALANCE: ${self.balance:,.2f}")
        for tx in self.transaction_history:
            print(f"[{tx['time']}] {tx['category']}: +${tx['amount']} | HASH: {tx['hash']}...")

# --- Simulation for the CEO ---
if __name__ == "__main__":
    vault = AletheiaVault(55500.00)
    vault.sign_transaction(15000, "SERIES_A_RETAINER")
    vault.get_audit_log()
