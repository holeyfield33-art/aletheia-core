"""Aletheia Core — Centralized configuration.

Loads from environment variables or config.yaml, with safe defaults.
All security-critical thresholds are defined here so they are auditable
in a single location.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]


_CONFIG_SEARCH_PATHS = [
    Path("config.yaml"),
    Path("config.yml"),
    Path(os.getenv("ALETHEIA_CONFIG_PATH", "")),
]


_MAX_CONFIG_SIZE = 100_000  # 100 KB — prevents YAML bomb variants


def _validate_config_ownership(config_path: Path) -> None:
    """Reject config files that are world/group-writable by non-owners.

    Prevents privilege escalation via tampered config on shared hosts.
    """
    import logging as _logging
    import stat
    _cfg_logger = _logging.getLogger("aletheia.config")
    try:
        st = config_path.stat()
        if st.st_uid != os.getuid() and (st.st_mode & 0o022):
            raise PermissionError(
                f"Config {config_path} is writable by others (mode={oct(st.st_mode)}). "
                f"Fix with: chmod go-w {config_path}"
            )
    except PermissionError:
        raise
    except OSError as exc:
        _cfg_logger.warning("Could not stat config %s: %s", config_path, exc)


def _load_yaml() -> dict:
    """Best-effort load of the first config file found on disk."""
    import logging as _logging
    _cfg_logger = _logging.getLogger("aletheia.config")
    for candidate in _CONFIG_SEARCH_PATHS:
        try:
            if candidate and candidate.is_file():
                _validate_config_ownership(candidate)
                raw = candidate.read_bytes()
                if len(raw) > _MAX_CONFIG_SIZE:
                    _cfg_logger.error(
                        "Config file %s exceeds %d bytes — skipped",
                        candidate, _MAX_CONFIG_SIZE,
                    )
                    continue
                data = yaml.safe_load(raw)
                return data if isinstance(data, dict) else {}
        except yaml.YAMLError as exc:
            _cfg_logger.error("Invalid YAML in %s: %s", candidate, exc)
            continue
        except Exception as exc:
            _cfg_logger.warning("Could not load config %s: %s", candidate, exc)
            continue
    return {}


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class AletheiaSettings:
    """Single source of truth for runtime configuration."""

    # --- Semantic intent analysis ---
    embedding_model: str = "all-MiniLM-L6-v2"
    intent_threshold: float = 0.55          # Judge veto cosine-sim threshold
    grey_zone_lower: float = 0.40           # Grey-zone second-pass lower bound
    nitpicker_similarity_threshold: float = 0.45  # Nitpicker blocked-pattern threshold

    # --- Polymorphic rotation (config-driven, deterministic cycle) ---
    polymorphic_modes: list[str] = field(
        default_factory=lambda: ["LINEAGE", "INTENT", "SKEPTIC"]
    )

    # --- Defence mode ---
    mode: str = "active"                     # "active" | "shadow" | "monitor"
    shadow_mode: bool = False                # Legacy compat — derived from mode

    # --- Logging ---
    log_level: str = "INFO"
    audit_log_path: str = "audit.log"

    # --- Policy ---
    policy_threshold: float = 7.5            # Scout threat-score threshold

    # --- Rate limiting ---
    rate_limit_per_second: int = 10

    # --- General ---
    client_id: str = "ALETHEIA_ENTERPRISE"

    def __post_init__(self) -> None:
        self.shadow_mode = self.mode == "shadow"
        # --- Enterprise threshold validation ---
        if not (0.0 <= self.intent_threshold <= 1.0):
            raise ValueError(
                f"intent_threshold must be in [0.0, 1.0], got {self.intent_threshold}"
            )
        if not (0.0 <= self.grey_zone_lower < self.intent_threshold):
            raise ValueError(
                f"grey_zone_lower ({self.grey_zone_lower}) must be in "
                f"[0.0, intent_threshold={self.intent_threshold})"
            )
        if not (0.0 <= self.nitpicker_similarity_threshold <= 1.0):
            raise ValueError(
                f"nitpicker_similarity_threshold must be in [0.0, 1.0], "
                f"got {self.nitpicker_similarity_threshold}"
            )
        if self.policy_threshold < 0:
            raise ValueError(
                f"policy_threshold must be >= 0, got {self.policy_threshold}"
            )
        if self.mode not in ("active", "shadow", "monitor"):
            raise ValueError(
                f"mode must be 'active', 'shadow', or 'monitor', got '{self.mode}'"
            )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def load(cls) -> "AletheiaSettings":
        """Merge: defaults ← yaml ← env vars (env wins)."""
        yaml_cfg = _load_yaml()

        def _get(key: str, default):
            env_val = _env(f"ALETHEIA_{key.upper()}")
            if env_val:
                # Coerce to the expected type
                if isinstance(default, float):
                    return float(env_val)
                if isinstance(default, int):
                    return int(env_val)
                if isinstance(default, bool):
                    return env_val.lower() in ("1", "true", "yes")
                if isinstance(default, list):
                    return [s.strip() for s in env_val.split(",")]
                return env_val
            return yaml_cfg.get(key, default)

        defaults = cls.__new__(cls)
        # Set raw defaults without validation for the _get helper
        defaults.embedding_model = "all-MiniLM-L6-v2"
        defaults.intent_threshold = 0.55
        defaults.grey_zone_lower = 0.40
        defaults.nitpicker_similarity_threshold = 0.45
        defaults.polymorphic_modes = ["LINEAGE", "INTENT", "SKEPTIC"]
        defaults.mode = "active"
        defaults.shadow_mode = False
        defaults.log_level = "INFO"
        defaults.audit_log_path = "audit.log"
        defaults.policy_threshold = 7.5
        defaults.rate_limit_per_second = 10
        defaults.client_id = "ALETHEIA_ENTERPRISE"
        return cls(
            embedding_model=_get("embedding_model", defaults.embedding_model),
            intent_threshold=_get("intent_threshold", defaults.intent_threshold),
            nitpicker_similarity_threshold=_get(
                "nitpicker_similarity_threshold",
                defaults.nitpicker_similarity_threshold,
            ),
            polymorphic_modes=_get("polymorphic_modes", defaults.polymorphic_modes),
            mode=_get("mode", defaults.mode),
            log_level=_get("log_level", defaults.log_level),
            audit_log_path=_get("audit_log_path", defaults.audit_log_path),
            policy_threshold=_get("policy_threshold", defaults.policy_threshold),
            rate_limit_per_second=_get("rate_limit_per_second", defaults.rate_limit_per_second),
            client_id=_get("client_id", defaults.client_id),
        )


# Module-level singleton — import and use directly.
settings: AletheiaSettings = AletheiaSettings.load()
