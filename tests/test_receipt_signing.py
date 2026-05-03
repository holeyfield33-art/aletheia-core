import hashlib
import hmac

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.audit import Receipt, build_tmr_receipt, verify_receipt


def _gen_keypair_pem() -> tuple[str, str]:
    sk = Ed25519PrivateKey.generate()
    priv_pem = sk.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")
    pub_pem = (
        sk.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return priv_pem, pub_pem


def _clear_ed25519_env(monkeypatch) -> None:
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_RECEIPT_PUBLIC_KEY_PATH", raising=False)


def _old_canonical_string(receipt: dict[str, str]) -> str:
    canonical = (
        f"{receipt['decision']}|{receipt['policy_hash']}|{receipt['policy_version']}|"
        f"{receipt['payload_sha256']}"
    )
    if "prompt" in receipt and receipt["prompt"] is not None:
        canonical += f"|prompt:{receipt['prompt']}"
    canonical += (
        f"|{receipt['action']}|{receipt['origin']}|{receipt['request_id']}|"
        f"{receipt['fallback_state']}|{receipt['issued_at']}|"
        f"{receipt['decision_token']}|{receipt['nonce']}"
    )
    return canonical


def test_ed25519_happy_path(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-ed-1",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )

    assert receipt["signature_algorithm"] == "ed25519"
    assert receipt.get("key_id")
    assert verify_receipt(receipt) is True


def test_ed25519_tamper_detection(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-ed-2",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    tampered = dict(receipt)
    tampered["decision"] = "DENIED"

    assert verify_receipt(tampered) is False


def test_hmac_backward_compat_path(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.setenv("ALETHEIA_RECEIPT_SECRET", "legacy-secret")

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-hmac-1",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )

    assert receipt["signature_algorithm"] == "hmac-sha256"
    assert "key_id" not in receipt
    assert verify_receipt(receipt) is True


def test_pre_migration_receipt_still_verifies(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    secret = "legacy-secret"  # pragma: allowlist secret
    monkeypatch.setenv("ALETHEIA_RECEIPT_SECRET", secret)

    legacy_receipt = {
        "decision": "PROCEED",
        "policy_hash": "abc123",
        "policy_version": "1.0",
        "payload_sha256": "deadbeef",
        "action": "Read_Report",
        "origin": "trusted_admin",
        "request_id": "req-legacy",
        "fallback_state": "normal",
        "decision_token": hashlib.sha256(
            b"req-legacy|2026-05-03T00:00:00+00:00|1.0|abc123|nonce-legacy"
        ).hexdigest(),
        "nonce": "nonce-legacy",
        "issued_at": "2026-05-03T00:00:00+00:00",
    }

    expected_sig = hmac.new(
        secret.encode("utf-8"),
        _old_canonical_string(legacy_receipt).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    legacy_receipt["signature"] = expected_sig

    # Explicitly assert old-schema receipts still parse with legacy defaults.
    parsed = Receipt.model_validate(dict(legacy_receipt))
    assert parsed.signature_algorithm == "hmac-sha256"
    assert parsed.key_id is None

    assert verify_receipt(legacy_receipt) is True


def test_algorithm_dispatch_missing_public_key(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)

    receipt = {
        "decision": "PROCEED",
        "policy_hash": "abc123",
        "policy_version": "1.0",
        "payload_sha256": "deadbeef",
        "action": "Read_Report",
        "origin": "trusted_admin",
        "request_id": "req-missing-pub",
        "fallback_state": "normal",
        "decision_token": "token",
        "nonce": "nonce",
        "issued_at": "2026-05-03T00:00:00+00:00",
        "signature_algorithm": "ed25519",
        "key_id": "1234567890abcdef",
        "signature": "00",
    }

    assert verify_receipt(receipt) is False


def test_wrong_key_tampering_fails(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)

    priv_a, pub_a = _gen_keypair_pem()
    priv_b, pub_b = _gen_keypair_pem()

    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_a)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub_a)
    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-key-a",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )

    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv_b)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub_b)
    assert verify_receipt(receipt) is False


def test_unknown_algorithm_returns_false(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    monkeypatch.setenv("ALETHEIA_RECEIPT_SECRET", "legacy-secret")

    receipt = {
        "decision": "PROCEED",
        "policy_hash": "abc123",
        "policy_version": "1.0",
        "payload_sha256": "deadbeef",
        "action": "Read_Report",
        "origin": "trusted_admin",
        "request_id": "req-unknown-alg",
        "fallback_state": "normal",
        "decision_token": "token",
        "nonce": "nonce",
        "issued_at": "2026-05-03T00:00:00+00:00",
        "signature_algorithm": "unknown",
        "signature": "abcd",
    }

    assert verify_receipt(receipt) is False


def test_both_algorithms_configured_prefers_ed25519(monkeypatch) -> None:
    _clear_ed25519_env(monkeypatch)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)
    monkeypatch.setenv("ALETHEIA_RECEIPT_SECRET", "legacy-secret")

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-both-configured",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )

    assert receipt["signature_algorithm"] == "ed25519"
    assert verify_receipt(receipt) is True


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------


def test_tamper_nonce_fails_ed25519(monkeypatch) -> None:
    """Mutating the nonce field after signing must invalidate an Ed25519 receipt."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-tamper-nonce",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    tampered = dict(receipt)
    tampered["nonce"] = "evil-nonce"
    assert verify_receipt(tampered) is False


def test_tamper_key_id_fails_ed25519(monkeypatch) -> None:
    """Mutating key_id after signing must invalidate the receipt."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-tamper-kid",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    tampered = dict(receipt)
    tampered["key_id"] = "0000000000000000"
    assert verify_receipt(tampered) is False


def test_hmac_wrong_secret_fails(monkeypatch) -> None:
    """HMAC receipt built with one secret must fail when verified with a different secret."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.setenv(
        "ALETHEIA_RECEIPT_SECRET", "secret-a"
    )  # pragma: allowlist secret

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-hmac-wrong-secret",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    assert receipt["signature_algorithm"] == "hmac-sha256"

    # Switch to a different secret before verifying
    monkeypatch.setenv(
        "ALETHEIA_RECEIPT_SECRET", "secret-b"
    )  # pragma: allowlist secret
    assert verify_receipt(receipt) is False


def test_prompt_field_included_in_canonical_string_ed25519(monkeypatch) -> None:
    """Receipt built with a prompt must fail if prompt is mutated after signing."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-prompt",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
        prompt="original prompt",
    )
    assert verify_receipt(receipt) is True

    tampered = dict(receipt)
    tampered["prompt"] = "injected prompt"
    assert verify_receipt(tampered) is False


def test_corrupted_signature_hex_returns_false(monkeypatch) -> None:
    """A receipt with a hex signature that is wrong length returns False, not an exception."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-corrupt-sig",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    corrupted = dict(receipt)
    corrupted["signature"] = "deadbeef"  # too short to be a valid Ed25519 signature
    assert verify_receipt(corrupted) is False


def test_verify_receipt_empty_dict_returns_false(monkeypatch) -> None:
    """verify_receipt() must not raise on a completely empty input — return False."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    assert verify_receipt({}) is False


def test_ed25519_receipt_fails_hmac_verification(monkeypatch) -> None:
    """An Ed25519-signed receipt must not accidentally verify against HMAC path."""
    _clear_ed25519_env(monkeypatch)
    monkeypatch.delenv("ALETHEIA_RECEIPT_SECRET", raising=False)
    priv, pub = _gen_keypair_pem()
    monkeypatch.setenv("ALETHEIA_RECEIPT_PRIVATE_KEY", priv)
    monkeypatch.setenv("ALETHEIA_RECEIPT_PUBLIC_KEY", pub)

    receipt = build_tmr_receipt(
        decision="PROCEED",
        policy_hash="abc123",
        policy_version="1.0",
        payload_sha256="deadbeef",
        action="Read_Report",
        origin="trusted_admin",
        request_id="req-crossalg",
        fallback_state="normal",
        issued_at="2026-05-03T00:00:00+00:00",
    )
    assert receipt["signature_algorithm"] == "ed25519"

    # Force algorithm to hmac-sha256 to simulate an algorithm-swap attack
    forged = dict(receipt)
    forged["signature_algorithm"] = "hmac-sha256"
    monkeypatch.setenv(
        "ALETHEIA_RECEIPT_SECRET", "any-secret"
    )  # pragma: allowlist secret
    assert verify_receipt(forged) is False
