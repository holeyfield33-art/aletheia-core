# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
import logging

from core.runtime_security import normalize_untrusted_text

_utils_logger = logging.getLogger("aletheia.bridge.utils")


def normalize_shadow_text(text: str, _depth: int = 0) -> str:
    """Legacy facade for runtime normalization.

    `_depth` is kept for backward compatibility with older call sites.
    """
    result = normalize_untrusted_text(text)
    if result.quarantined:
        _utils_logger.warning(
            "Input quarantined by runtime normalization: reason=%s",
            result.quarantine_reason,
        )
    return result.normalized_form
