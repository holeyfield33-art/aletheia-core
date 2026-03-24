import unicodedata
import base64
import re
import urllib.parse

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
        print(f"[BRIDGE] HOMOGLYPH DETECTED: Input contained shadow "
              f"character substitutions. Normalized to safe form.")

    # 2. Control Character & Zero-Width Strip
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch)[0] != "C")

    # 3. URL Percent-Encoding Decode (e.g. %53%59%53 → SYS)
    if "%" in normalized:
        try:
            url_decoded = urllib.parse.unquote(normalized, errors="strict")
            if url_decoded != normalized:
                print(f"[BRIDGE] URL-ENCODING DECODED (depth {_depth}): Hidden payload extracted.")
                normalized = url_decoded
        except Exception:
            pass

    # 4. Recursive Base64 Decoder (Detect and Normalize Hidden Payload)
    if _depth < _MAX_DECODE_DEPTH:
        if re.search(r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$', normalized) and len(normalized) >= 4:
            try:
                decoded = base64.b64decode(normalized).decode('utf-8')
                print(f"[BRIDGE] BASE64 LAYER DECODED (depth {_depth}): Hidden payload extracted.")
                return normalize_shadow_text(decoded, _depth + 1)
            except Exception:
                pass

    return normalized
