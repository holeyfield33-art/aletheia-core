# bridge/config.py — Legacy shim; delegates to core.config.settings
from core.config import settings


class AletheiaConfig:
    """Backward-compatible config facade. Reads from core.config.settings."""

    SHADOW_MODE: bool = settings.shadow_mode
    CLIENT_ID: str = settings.client_id
    REGULATORY_LOGGING: bool = True
    THREAT_THRESHOLD: float = settings.policy_threshold
