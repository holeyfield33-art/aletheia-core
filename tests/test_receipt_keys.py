"""Unit tests for core/receipt_keys.py."""

from __future__ import annotations

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _generate_pem_pair() -> tuple[str, str]:
    """Return (private_pem, public_pem) as strings for a fresh Ed25519 keypair."""
    sk = Ed25519PrivateKey.generate()
    priv = sk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub = (
        sk.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return priv, pub


# ---------------------------------------------------------------------------
# load_private_key()
# ---------------------------------------------------------------------------


def test_load_private_key_from_env_var(monkeypatch):
    """load_private_key() resolves from ALETHEIA_RECEIPT_PRIVATE_KEY env var."""
    priv_pem, _ = _generate_pem_pair()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import load_private_key

    key = load_private_key()
    assert isinstance(key, Ed25519PrivateKey)


def test_load_private_key_from_file_path(monkeypatch, tmp_path):
    """load_private_key() resolves from ALETHEIA_RECEIPT_PRIVATE_KEY_PATH env var."""
    priv_pem, _ = _generate_pem_pair()
    key_file = tmp_path / "receipt_private.pem"
    key_file.write_text(priv_pem)

    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", str(key_file))

    from core.receipt_keys import load_private_key

    key = load_private_key()
    assert isinstance(key, Ed25519PrivateKey)


def test_load_private_key_missing_raises(monkeypatch):
    """load_private_key() raises ReceiptKeyError when no key is configured."""
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import load_private_key, ReceiptKeyError

    with pytest.raises(ReceiptKeyError, match="Receipt private key not configured"):
        load_private_key()


def test_load_private_key_malformed_raises(monkeypatch):
    """load_private_key() raises ReceiptKeyError for malformed PEM."""
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", "not-a-valid-pem")
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import load_private_key, ReceiptKeyError

    with pytest.raises(ReceiptKeyError, match="Failed to parse receipt private key"):
        load_private_key()


# ---------------------------------------------------------------------------
# load_public_key() — derive from private when no public key set
# ---------------------------------------------------------------------------


def test_load_public_key_derived_from_private(monkeypatch):
    """load_public_key() derives from the private key when no explicit public key is set."""
    priv_pem, pub_pem = _generate_pem_pair()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import load_public_key, load_private_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    pub = load_public_key()
    assert isinstance(pub, Ed25519PublicKey)

    # Must match the public key derived directly from the private key
    expected_bytes = (
        load_private_key()
        .public_key()
        .public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    )
    actual_bytes = pub.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    assert actual_bytes == expected_bytes


# ---------------------------------------------------------------------------
# key_id() — stable across calls
# ---------------------------------------------------------------------------


def test_key_id_stable_across_calls(monkeypatch):
    """key_id() returns the same 16-char hex string on repeated calls."""
    priv_pem, _ = _generate_pem_pair()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import key_id

    kid1 = key_id()
    kid2 = key_id()
    assert kid1 == kid2
    assert len(kid1) == 16
    # Must be valid hex
    int(kid1, 16)


# ---------------------------------------------------------------------------
# is_configured()
# ---------------------------------------------------------------------------


def test_is_configured_true_when_private_key_set(monkeypatch):
    priv_pem, _ = _generate_pem_pair()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import is_configured

    assert is_configured() is True


def test_is_configured_false_when_no_key(monkeypatch):
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import is_configured

    assert is_configured() is False
