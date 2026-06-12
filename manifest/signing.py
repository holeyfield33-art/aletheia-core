# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Ashura Joseph Holeyfield - Aletheia Sovereign Systems
import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import logging as _logging

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_signing_logger = _logging.getLogger("aletheia.signing")

# Grace period: manifests within this window of expiry produce a warning
# but are still accepted. Beyond this, they are hard-rejected. This is the
# default for non-production environments; production fails closed (0 days)
# unless ALETHEIA_MANIFEST_GRACE_DAYS overrides it. See _grace_period_days().
_GRACE_PERIOD_DAYS = 7


def _grace_period_days() -> int:
    """Resolve the expiry grace window.

    Order of precedence:
      1. ALETHEIA_MANIFEST_GRACE_DAYS (explicit operator override, >= 0)
      2. 0 in production (fail-closed: an expired manifest is rejected)
      3. _GRACE_PERIOD_DAYS otherwise (developer convenience)
    """
    raw = os.getenv("ALETHEIA_MANIFEST_GRACE_DAYS", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            _signing_logger.warning(
                "Invalid ALETHEIA_MANIFEST_GRACE_DAYS=%r; using default.", raw
            )
    if os.getenv("ENVIRONMENT", "").strip().lower() not in {
        "development",
        "dev",
        "test",
        "testing",
        "local",
    }:
        return 0
    return _GRACE_PERIOD_DAYS


class ManifestTamperedError(RuntimeError):
    """Raised when manifest integrity verification fails."""


@dataclass(frozen=True)
class ManifestSignature:
    algorithm: str
    key_id: str
    key_version: str
    manifest_version: str
    payload_sha256: str
    signature_b64: str
    signed_at: str
    expires_at: str

    def as_json(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "key_version": self.key_version,
            "manifest_version": self.manifest_version,
            "payload_sha256": self.payload_sha256,
            "signature": self.signature_b64,
            "signed_at": self.signed_at,
            "expires_at": self.expires_at,
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return _repo_root() / candidate


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise ManifestTamperedError(f"Required file missing: {path}") from exc


def _public_key_id(public_key: Ed25519PublicKey) -> str:
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(public_raw).hexdigest()


def _load_manifest_metadata(payload: bytes) -> tuple[str, str]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise ManifestTamperedError("Manifest is not valid JSON.") from exc

    version = str(data.get("version", "")).strip()
    expires_at = str(data.get("expires_at", "")).strip()
    if not version:
        raise ManifestTamperedError("Manifest version is required.")
    if not expires_at:
        raise ManifestTamperedError("Manifest expires_at is required.")
    return version, expires_at


def _load_private_key(private_key_path: Path) -> Ed25519PrivateKey:
    key_bytes = _read_bytes(private_key_path)
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ManifestTamperedError(
            f"Manifest private key at {private_key_path} must be Ed25519, "
            f"got {type(private_key).__name__}"
        )
    return private_key


def _load_public_key(public_key_path: Path) -> Ed25519PublicKey:
    key_bytes = _read_bytes(public_key_path)
    pub_key = serialization.load_pem_public_key(key_bytes)
    if not isinstance(pub_key, Ed25519PublicKey):
        raise ManifestTamperedError(
            f"Manifest public key at {public_key_path} must be Ed25519, "
            f"got {type(pub_key).__name__}"
        )
    return pub_key


def generate_keypair(private_key_path: str | Path, public_key_path: str | Path) -> None:
    private_path = _resolve_path(private_key_path)
    public_path = _resolve_path(public_key_path)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_pem)
    os.chmod(private_path, 0o600)
    public_path.write_bytes(public_pem)


def sign_manifest(
    manifest_path: str | Path,
    signature_path: str | Path,
    private_key_path: str | Path,
    public_key_path: str | Path,
) -> Path:
    manifest = _resolve_path(manifest_path)
    signature = _resolve_path(signature_path)
    private_path = _resolve_path(private_key_path)
    public_path = _resolve_path(public_key_path)

    if not private_path.exists() or not public_path.exists():
        generate_keypair(private_path, public_path)

    payload = _read_bytes(manifest)
    manifest_version, expires_at = _load_manifest_metadata(payload)
    payload_hash = hashlib.sha256(payload).hexdigest()

    private_key = _load_private_key(private_path)
    public_key = _load_public_key(public_path)
    signature_bytes = private_key.sign(payload)

    signed = ManifestSignature(
        algorithm="ed25519",
        key_id=_public_key_id(public_key),
        key_version=os.getenv("ALETHEIA_MANIFEST_KEY_VERSION", "v1"),
        manifest_version=manifest_version,
        payload_sha256=payload_hash,
        signature_b64=base64.b64encode(signature_bytes).decode("ascii"),
        signed_at=datetime.now(timezone.utc).isoformat(),
        expires_at=expires_at,
    )

    signature.write_text(json.dumps(signed.as_json(), indent=2), encoding="utf-8")
    return signature


def verify_manifest_signature(
    manifest_path: str | Path,
    signature_path: str | Path,
    public_key_path: str | Path,
) -> None:
    """Security-critical gate: manifest is rejected if detached signature fails."""
    manifest = _resolve_path(manifest_path)
    signature = _resolve_path(signature_path)
    public_path = _resolve_path(public_key_path)

    payload = _read_bytes(manifest)
    manifest_version, manifest_expires_at = _load_manifest_metadata(payload)
    payload_hash = hashlib.sha256(payload).hexdigest()

    public_key = _load_public_key(public_path)
    expected_key_id = _public_key_id(public_key)

    # Out-of-band trust anchor: when an expected key fingerprint is pinned via
    # ALETHEIA_MANIFEST_EXPECTED_KEY_ID, reject any on-disk public key that does
    # not match it. Without this, an attacker who can write the deploy directory
    # could replace manifest + signature + public key as a set and still pass
    # verification — the signature alone only proves self-consistency.
    pinned_key_id = os.getenv("ALETHEIA_MANIFEST_EXPECTED_KEY_ID", "").strip()
    if pinned_key_id and pinned_key_id.lower() != expected_key_id.lower():
        raise ManifestTamperedError(
            "Manifest public key fingerprint does not match the pinned "
            "ALETHEIA_MANIFEST_EXPECTED_KEY_ID."
        )

    try:
        signature_data = json.loads(_read_bytes(signature).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestTamperedError(
            "Manifest signature file is not valid JSON."
        ) from exc

    required_fields = {
        "algorithm",
        "key_id",
        "key_version",
        "manifest_version",
        "payload_sha256",
        "signature",
        "signed_at",
        "expires_at",
    }
    if not required_fields.issubset(signature_data):
        raise ManifestTamperedError("Manifest signature file missing required fields.")

    if signature_data["algorithm"] != "ed25519":
        raise ManifestTamperedError("Unsupported manifest signature algorithm.")

    if signature_data["key_id"] != expected_key_id:
        raise ManifestTamperedError("Manifest signature key mismatch.")

    expected_key_version = os.getenv("ALETHEIA_MANIFEST_KEY_VERSION", "v1")
    if signature_data["key_version"] != expected_key_version:
        raise ManifestTamperedError("Manifest signature key version mismatch.")

    if signature_data["manifest_version"] != manifest_version:
        raise ManifestTamperedError("Manifest version drift detected.")

    if signature_data["expires_at"] != manifest_expires_at:
        raise ManifestTamperedError("Manifest expiry metadata mismatch.")

    try:
        expiry = datetime.fromisoformat(
            str(signature_data["expires_at"]).replace("Z", "+00:00")
        )
    except Exception as exc:
        raise ManifestTamperedError("Manifest expiry is malformed.") from exc

    now = datetime.now(timezone.utc)
    from datetime import timedelta

    grace_days = _grace_period_days()
    grace_deadline = expiry + timedelta(days=grace_days)

    if now > grace_deadline:
        raise ManifestTamperedError(
            f"Manifest expired on {expiry.isoformat()} and the "
            f"{grace_days}-day grace period has elapsed."
        )
    if now > expiry:
        days_past = (now - expiry).days
        _signing_logger.warning(
            "Manifest expired %d day(s) ago on %s. "
            "Grace period: %d of %d days remaining. "
            "Re-sign the manifest before the grace period ends.",
            days_past,
            expiry.isoformat(),
            grace_days - days_past,
            grace_days,
        )

    if signature_data["payload_sha256"] != payload_hash:
        raise ManifestTamperedError("Manifest hash mismatch; file has been modified.")

    try:
        signature_bytes = base64.b64decode(signature_data["signature"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ManifestTamperedError("Manifest signature encoding is invalid.") from exc

    if len(signature_bytes) != 64:
        raise ManifestTamperedError("Manifest signature length is invalid.")

    try:
        public_key.verify(signature_bytes, payload)
    except Exception as exc:
        raise ManifestTamperedError("Manifest signature verification failed.") from exc
