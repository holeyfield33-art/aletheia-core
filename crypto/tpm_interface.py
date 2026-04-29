"""TPM 2.0 interface for hardware-bound identity and chain signing.

Falls back to Ed25519 software signing when TPM hardware is unavailable.
The TPM backend is gated behind the ``tpm2-pytss`` optional dependency.

Security note: software fallback is **not** FIPS 140-3 Level 2 —
it protects chain integrity but not against host-level key extraction.
Set ``ALETHEIA_REQUIRE_TPM=true`` in production to hard-fail without TPM.
"""

from __future__ import annotations

import fcntl
import logging
import os
import time

from core.config import env_bool
from typing import Protocol

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_logger = logging.getLogger("aletheia.crypto.tpm")

_TPM_PERSISTENT_HANDLE = 0x81000001
_NV_BASE = 0x01800000


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
                self._private = serialization.load_pem_private_key(
                    fh.read(), password=None
                )  # type: ignore[assignment]
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
            _logger.info(
                "Loaded TPM persistent key at handle 0x%08X", _TPM_PERSISTENT_HANDLE
            )
        except Exception:
            primary = self._ctx.create_primary(alg="ecc", curve="NIST_P256")
            self._key_handle = self._ctx.evict_control(
                primary.handle,
                persistent_handle=_TPM_PERSISTENT_HANDLE,
            )
            _logger.info(
                "Created new TPM primary key at handle 0x%08X", _TPM_PERSISTENT_HANDLE
            )

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

    def nv_read_counter(self, counter_index: int) -> int:
        """Read NV counter value."""
        nv_index = _NV_BASE + counter_index
        result = self._ctx.NV_Read(nv_index)
        return int.from_bytes(result, byteorder="big")

    def nv_increment_counter(self, counter_index: int) -> int:
        """Atomically increment TPM NV counter via NV_Increment."""
        nv_index = _NV_BASE + counter_index
        self._ctx.NV_Increment(nv_index)
        return self.nv_read_counter(counter_index)


# ---------------------------------------------------------------------------
# TPMAnchor — unified entry point
# ---------------------------------------------------------------------------
class TPMAnchor:
    """Hardware-bound (or software-fallback) signing anchor.

    Computes SHA3-256(request || response || nonce) and signs the digest.
    """

    def __init__(self) -> None:
        require_tpm = env_bool("ALETHEIA_REQUIRE_TPM")
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

    # ------------------------------------------------------------------
    # Monotonic counter (anti-rollback)
    # ------------------------------------------------------------------
    @property
    def _counter_log_path(self) -> str:
        return os.getenv(
            "ALETHEIA_COUNTER_LOG_PATH",
            "/var/lib/aletheia/counter.log",
        )

    def get_monotonic_counter(self, counter_index: int = 0) -> int | None:
        """Read monotonic counter from TPM NVRAM or signed log fallback.

        Returns ``None`` only when TPM NV read fails (no safe fallback to
        Ed25519 log from an ECDSA backend).
        """
        if self.backend_type == "tpm":
            try:
                return self._backend.nv_read_counter(counter_index)  # type: ignore[attr-defined]
            except Exception as exc:
                _logger.warning("TPM counter read failed: %s", exc)
                return None
        return self._get_counter_from_signed_log()

    def increment_monotonic_counter(self, counter_index: int = 0) -> bool:
        """Atomically increment monotonic counter.

        TPM path uses ``NV_Increment`` (single atomic TPM command).
        Software fallback uses a signed append-only log with file locking.
        """
        if self.backend_type == "tpm":
            try:
                self._backend.nv_increment_counter(counter_index)  # type: ignore[attr-defined]
                return True
            except Exception as exc:
                _logger.error("TPM counter increment failed: %s", exc)
                return False
        return self._increment_counter_in_signed_log()

    def _get_counter_from_signed_log(self) -> int:
        """Read highest verified nonce from signed append-only log."""
        log_path = self._counter_log_path
        try:
            with open(log_path, "r") as fh:
                fcntl.flock(fh, fcntl.LOCK_SH)
                try:
                    return self._read_verified_counter(fh)
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        except FileNotFoundError:
            return 0

    def _increment_counter_in_signed_log(self) -> bool:
        """Append signed counter entry under exclusive lock (atomic read+write)."""
        log_path = self._counter_log_path
        old_umask = os.umask(0o077)
        try:
            with open(log_path, "a+") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                try:
                    fh.seek(0)
                    highest = self._read_verified_counter(fh)
                    new_value = highest + 1
                    timestamp = int(time.time() * 1000)
                    entry = f"{timestamp} {new_value}"
                    signature = self._backend.sign(entry.encode())
                    fh.write(f"{entry} {signature.hex()}\n")
                    fh.flush()
                finally:
                    fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError as exc:
            _logger.error("Counter log write failed: %s", exc)
            return False
        finally:
            os.umask(old_umask)
        return True

    def _read_verified_counter(self, fh) -> int:
        """Parse and verify counter entries from an open file handle."""
        highest = 0
        pub = self._backend.public_key_bytes()
        vk = Ed25519PublicKey.from_public_bytes(pub)
        for line in fh:
            parts = line.strip().split()
            if len(parts) != 3:
                continue
            try:
                nonce = int(parts[1])
                sig = bytes.fromhex(parts[2])
            except (ValueError, IndexError):
                continue
            message = f"{parts[0]} {parts[1]}".encode()
            try:
                vk.verify(sig, message)
                highest = max(highest, nonce)
            except Exception:
                _logger.debug("Skipping unverifiable counter entry")
        return highest
