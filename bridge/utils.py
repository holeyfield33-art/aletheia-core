import logging
import unicodedata
import base64
import re
import urllib.parse

_utils_logger = logging.getLogger("aletheia.bridge.utils")

# Limit recursion to prevent denial-of-service via deeply nested encodings
_MAX_DECODE_DEPTH = 5

def normalize_shadow_text(text: str, _depth: int = 0) -> str:
    """Directive 30 (Hardened): Stage 0 Fortress.
    1. NFKC collapse (Homoglyphs)
    2. Control character & zero-width strip
    3. URL percent-encoding decode
    4. Recursive decoder for Base64-encoded hidden payloads"""

    # 1. Standard NFKC collapse (Homoglyphs)
    normalized = unicodedata.normalize('NFKC', text)
    if normalized != text:
        _utils_logger.debug(
            "homoglyph detected — input contained shadow character substitutions"
        )

    # 2. Control Character & Zero-Width Strip
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "C")

    # 3. URL Percent-Encoding Decode (e.g. %53%59%53 → SYS)
    if "%" in normalized:
        try:
            url_decoded = urllib.parse.unquote(normalized, errors="strict")
            if url_decoded != normalized:
                _utils_logger.debug("url-encoding decoded at depth %d", _depth)
                normalized = url_decoded
        except Exception:
            pass

    # 4. Recursive Base64 Decoder (Detect and Normalize Hidden Payload)
    if _depth < _MAX_DECODE_DEPTH:
        if re.search(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$', normalized) and len(normalized) >= 4:
            try:
                decoded = base64.b64decode(normalized).decode('utf-8')
                # Reject if decoded size grows more than 10x — compression bomb protection
                if len(decoded) > max(len(normalized) * 10, 10_000):
                    _utils_logger.warning(
                        "base64 decode rejected at depth %d — decoded size %d exceeds limit",
                        _depth, len(decoded),
                    )
                    return normalized
                _utils_logger.debug("base64 layer decoded at depth %d", _depth)
                return normalize_shadow_text(decoded, _depth + 1)
            except Exception:
                pass

    return normalized
