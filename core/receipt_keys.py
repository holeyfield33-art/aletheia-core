"""Ed25519 keypair management for receipt signing.

Receipt signing uses Ed25519 (FIPS 186-5 approved). The private key signs
receipts at the engine; the public key is published at /.well-known/
aletheia-receipt-key.pem so third parties (and the aletheia-redteam-kit)
can verify receipt signatures without trust in the engine.
"""

from __future__ import annotations

import base64  # noqa: F401  (imported for API symmetry with manifest/signing.py)
import hashlib
import os
from pathlib import Path
from typing import Optional  # noqa: F401

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class ReceiptKeyError(RuntimeError):
    """Raised when receipt keys are missing, malformed, or unloadable."""


def load_private_key() -> Ed25519PrivateKey:
    """Load the Ed25519 receipt-signing private key.

    Resolution order:
      1. ALETHEIA_RECEIPT_PRIVATE_KEY env var (PEM, multiline OK)
      2. ALETHEIA_RECEIPT_PRIVATE_KEY_PATH env var (filesystem path)

    Raises ReceiptKeyError if neither is set or the key cannot be parsed.
    """
    pem = os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY", "").strip()
    if not pem:
        path = os.getenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", "").strip()
        if path:
            try:
                pem = Path(path).read_text()
            except OSError as exc:
                raise ReceiptKeyError(
                    f"Cannot read ALETHEIA_RECEIPT_PRIVATE_KEY_PATH={path}: {exc}"
                ) from exc
    if not pem:
        raise ReceiptKeyError(
            "Receipt private key not configured. Set "
            "ALETHEIA_RECEIPT_PRIVATE_KEY (PEM) or "
            "ALETHEIA_RECEIPT_PRIVATE_KEY_PATH (file path)."
        )
    try:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    except Exception as exc:
        raise ReceiptKeyError(f"Failed to parse receipt private key: {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise ReceiptKeyError(
            f"Receipt private key must be Ed25519, got {type(key).__name__}"
        )
    return key


def load_public_key() -> Ed25519PublicKey:
    """Load the Ed25519 receipt public key.

    Resolution order:
      1. ALETHEIA_RECEIPT_PUBLIC_KEY env var (PEM)
      2. ALETHEIA_RECEIPT_PUBLIC_KEY_PATH env var (filesystem path)
      3. Derived from the private key via load_private_key()

    Raises ReceiptKeyError if no source resolves.
    """
    pem = os.getenv("ALETHEIA_RECEIPT_PUBLIC_KEY", "").strip()
    if not pem:
        path = os.getenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", "").strip()
        if path:
            try:
                pem = Path(path).read_text()
            except OSError as exc:
                raise ReceiptKeyError(
                    f"Cannot read ALETHEIA_RECEIPT_PUBLIC_KEY_PATH={path}: {exc}"
                ) from exc
    if pem:
        try:
            key = serialization.load_pem_public_key(pem.encode("utf-8"))
        except Exception as exc:
            raise ReceiptKeyError(f"Failed to parse receipt public key: {exc}") from exc
        if not isinstance(key, Ed25519PublicKey):
            raise ReceiptKeyError(
                f"Receipt public key must be Ed25519, got {type(key).__name__}"
            )
        return key
    # Fallback: derive from private key
    return load_private_key().public_key()


def public_key_pem() -> bytes:
    """Return the public key as PEM bytes for serving via HTTP route."""
    return load_public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def key_id() -> str:
    """Return a stable key ID (first 16 hex chars of SHA-256 of public-key DER)."""
    der = load_public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()[:16]


def is_configured() -> bool:
    """True if Ed25519 receipt signing is available. Used for fallback decisions."""
    try:
        load_private_key()
        return True
    except ReceiptKeyError:
        return False
