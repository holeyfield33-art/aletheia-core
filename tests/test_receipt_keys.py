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


# ---------------------------------------------------------------------------
# load_public_key() — explicit env var and file path resolution
# ---------------------------------------------------------------------------


def test_load_public_key_from_env_var(monkeypatch):
    """load_public_key() resolves from ALETHEIA_RECEIPT_PUBLIC_KEY env var directly."""
    priv_pem, pub_pem = _generate_pem_pair()
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import load_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    pub = load_public_key()
    assert isinstance(pub, Ed25519PublicKey)


def test_load_public_key_from_file_path(monkeypatch, tmp_path):
    """load_public_key() resolves from ALETHEIA_RECEIPT_PUBLIC_KEY_PATH env var."""
    _, pub_pem = _generate_pem_pair()
    key_file = tmp_path / "receipt_public.pem"
    key_file.write_text(pub_pem)

    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", str(key_file))

    from core.receipt_keys import load_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    pub = load_public_key()
    assert isinstance(pub, Ed25519PublicKey)


def test_load_public_key_no_source_raises(monkeypatch):
    """load_public_key() raises ReceiptKeyError when no key is reachable."""
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import load_public_key, ReceiptKeyError

    with pytest.raises(ReceiptKeyError):
        load_public_key()


# ---------------------------------------------------------------------------
# public_key_pem() — returns PEM bytes
# ---------------------------------------------------------------------------


def test_public_key_pem_returns_pem_bytes(monkeypatch):
    """public_key_pem() returns bytes starting with -----BEGIN PUBLIC KEY-----."""
    priv_pem, _ = _generate_pem_pair()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_pem)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import public_key_pem

    pem = public_key_pem()
    assert isinstance(pem, bytes)
    assert pem.startswith(b"-----BEGIN PUBLIC KEY-----")


# ---------------------------------------------------------------------------
# key_id() — uniqueness and error cases
# ---------------------------------------------------------------------------


def test_key_id_distinct_for_different_keypairs(monkeypatch):
    """key_id() returns different values for two different key pairs."""
    priv_a, _ = _generate_pem_pair()
    priv_b, _ = _generate_pem_pair()
    assert priv_a != priv_b

    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)

    from core.receipt_keys import key_id

    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_a)
    kid_a = key_id()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_b)
    kid_b = key_id()

    assert kid_a != kid_b


def test_key_id_raises_when_no_key_configured(monkeypatch):
    """key_id() raises ReceiptKeyError when no private or public key is set."""
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)

    from core.receipt_keys import key_id, ReceiptKeyError

    with pytest.raises(ReceiptKeyError):
        key_id()


# ---------------------------------------------------------------------------
# load_private_key() — env var takes precedence over file path
# ---------------------------------------------------------------------------


def test_load_private_key_env_var_takes_precedence_over_file_path(
    monkeypatch, tmp_path
):
    """ALETHEIA_RECEIPT_PRIVATE_KEY (env) resolved before PRIVATE_KEY_PATH (file)."""
    priv_env, _ = _generate_pem_pair()
    priv_file, _ = _generate_pem_pair()
    key_file = tmp_path / "receipt_private.pem"
    key_file.write_text(priv_file)

    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_env)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", str(key_file))

    from core.receipt_keys import load_private_key

    key = load_private_key()
    # Compare public key fingerprints as a proxy (avoids needing priv bytes equality)
    from cryptography.hazmat.primitives import serialization as ser

    expected_pub = serialization.load_pem_private_key(
        priv_env.encode(), password=None
    ).public_key()
    actual_pub = key.public_key()
    assert expected_pub.public_bytes(
        ser.Encoding.Raw, ser.PublicFormat.Raw
    ) == actual_pub.public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)
