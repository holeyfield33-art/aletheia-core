# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
# Aletheia Core — Configuration & Shared Utilities
from core.text_normalization import collapse_confusables  # noqa: F401
from core.canonicalization import (  # noqa: F401
    CanonicalGate,
    CanonicalPolicy,
    CanonicalResult,
    canonicalize_untrusted_text,
)
