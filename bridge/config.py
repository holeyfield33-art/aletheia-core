# bridge/config.py
class AletheiaConfig:
    # SHADOW_MODE: True = Log and Alert only | False = Active Blocking
    SHADOW_MODE = True 
    CLIENT_ID = "LUNAR_CREDIT_BETA"
    REGULATORY_LOGGING = True # Enables compliance trails for EU AI Act Article 6
    THREAT_THRESHOLD = 7.5    # Stricter threshold for Fintech-Class
