"""TPM 2.0 interface for hardware-bound identity and chain signing.

Falls back to Ed25519 software signing when TPM hardware is unavailable.
The TPM backend is gated behind the ``tpm2-pytss`` optional dependency.

Security note: software fallback is **not** FIPS 140-3 Level 2 —
it protects chain integrity but not against host-level key extraction.
Set ``ALETHEIA_REQUIRE_TPM=true`` in production to hard-fail without TPM.
"""
from __future__ import annotations

import logging
import os
from typing import Protocol

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_logger = logging.getLogger("aletheia.crypto.tpm")

_TPM_PERSISTENT_HANDLE = 0x81000001


# ---------------------------------------------------------------------------
# Abstract signing interface
# ---------------------------------------------------------------------------
class SigningBackend(Protocol):
    """Minimal interface shared by TPM and software signers."""

    def sign(self, digest: bytes) -> bytes: ...
    def public_key_bytes(self) -> bytes: ...


# ---------------------------------------------------------------------------
# Software (Ed25519) fallback
# ---------------------------------------------------------------------------
class _SoftwareBackend:
    """Ed25519 signing using ``cryptography``.

    Key material lives in-memory; optionally persisted to
    ``ALETHEIA_CHAIN_KEY_PATH`` (PEM, no passphrase — protect with FS perms).
    """

    def __init__(self) -> None:
        key_path = os.getenv("ALETHEIA_CHAIN_KEY_PATH", "").strip()
        if key_path and os.path.isfile(key_path):
            with open(key_path, "rb") as fh:
                self._private = serialization.load_pem_private_key(fh.read(), password=None)  # type: ignore[assignment]
            _logger.info("Loaded chain signing key from %s", key_path)
        else:
            self._private = Ed25519PrivateKey.generate()
            _logger.warning(
                "Generated ephemeral Ed25519 chain key (not persisted). "
                "Set ALETHEIA_CHAIN_KEY_PATH for key persistence across restarts."
            )
            if key_path:
                try:
                    pem = self._private.private_bytes(
                        serialization.Encoding.PEM,
                        serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption(),
                    )
                    old_umask = os.umask(0o077)
                    try:
                        with open(key_path, "wb") as fh:
                            fh.write(pem)
                    finally:
                        os.umask(old_umask)
                    _logger.info("Persisted new chain signing key to %s", key_path)
                except OSError as exc:
                    _logger.error("Failed to persist chain key: %s", exc)

    def sign(self, digest: bytes) -> bytes:
        return self._private.sign(digest)

    def public_key_bytes(self) -> bytes:
        pub: Ed25519PublicKey = self._private.public_key()  # type: ignore[assignment]
        return pub.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )


# ---------------------------------------------------------------------------
# TPM 2.0 backend (optional)
# ---------------------------------------------------------------------------
class _TPMBackend:
    """Hardware-bound signing via TPM 2.0 (requires ``tpm2-pytss``)."""

    def __init__(self, tpm_dev: str = "/dev/tpm0") -> None:
        try:
            from tpm2_pytss import ESAPI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "tpm2-pytss is not installed. "
                "Install with: pip install 'aletheia-cyber-core[tpm]'"
            ) from exc

        self._ctx = ESAPI(tpm_dev)
        self._key_handle = None
        self._load_or_create_key()

    def _load_or_create_key(self) -> None:
        try:
            self._key_handle = self._ctx.load_persistent(_TPM_PERSISTENT_HANDLE)
            _logger.info("Loaded TPM persistent key at handle 0x%08X", _TPM_PERSISTENT_HANDLE)
        except Exception:
            primary = self._ctx.create_primary(alg="ecc", curve="NIST_P256")
            self._key_handle = self._ctx.evict_control(
                primary.handle,
                persistent_handle=_TPM_PERSISTENT_HANDLE,
            )
            _logger.info("Created new TPM primary key at handle 0x%08X", _TPM_PERSISTENT_HANDLE)

    def sign(self, digest: bytes) -> bytes:
        sig = self._ctx.sign(
            self._key_handle,
            digest,
            scheme={"alg": "ECDSA", "hash": "SHA256"},
        )
        return bytes(sig)

    def public_key_bytes(self) -> bytes:
        pub = self._ctx.read_public(self._key_handle)
        return bytes(pub)


# ---------------------------------------------------------------------------
# TPMAnchor — unified entry point
# ---------------------------------------------------------------------------
class TPMAnchor:
    """Hardware-bound (or software-fallback) signing anchor.

    Computes SHA3-256(request || response || nonce) and signs the digest.
    """

    def __init__(self) -> None:
        require_tpm = os.getenv("ALETHEIA_REQUIRE_TPM", "").lower() in ("true", "1", "yes")
        tpm_dev = os.getenv("ALETHEIA_TPM_DEVICE", "/dev/tpm0")

        backend: SigningBackend | None = None

        if os.path.exists(tpm_dev):
            try:
                backend = _TPMBackend(tpm_dev)
                _logger.info("TPM backend active (%s)", tpm_dev)
            except Exception as exc:
                _logger.warning("TPM initialisation failed: %s", exc)

        if backend is None:
            if require_tpm:
                raise RuntimeError(
                    "ALETHEIA_REQUIRE_TPM=true but TPM is not available. "
                    "Refusing to start without hardware-bound signing."
                )
            backend = _SoftwareBackend()
            _logger.info("Using Ed25519 software signing fallback")

        self._backend: SigningBackend = backend

    def sign_chain(self, request: bytes, response: bytes, nonce: bytes) -> bytes:
        """Sign the full chain: SHA3-256(R || S || nonce)."""
        h = hashes.Hash(hashes.SHA3_256())
        h.update(request)
        h.update(response)
        h.update(nonce)
        digest = h.finalize()
        return self._backend.sign(digest)

    def public_key_bytes(self) -> bytes:
        return self._backend.public_key_bytes()

    @property
    def backend_type(self) -> str:
        if isinstance(self._backend, _TPMBackend):
            return "tpm"
        return "software"
