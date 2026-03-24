import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


class ManifestTamperedError(RuntimeError):
    """Raised when manifest integrity verification fails."""


@dataclass(frozen=True)
class ManifestSignature:
    algorithm: str
    key_id: str
    payload_sha256: str
    signature_b64: str
    signed_at: str

    def as_json(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "key_id": self.key_id,
            "payload_sha256": self.payload_sha256,
            "signature": self.signature_b64,
            "signed_at": self.signed_at,
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


def _load_private_key(private_key_path: Path) -> Ed25519PrivateKey:
    key_bytes = _read_bytes(private_key_path)
    return serialization.load_pem_private_key(key_bytes, password=None)


def _load_public_key(public_key_path: Path) -> Ed25519PublicKey:
    key_bytes = _read_bytes(public_key_path)
    pub_key = serialization.load_pem_public_key(key_bytes)
    if not isinstance(pub_key, Ed25519PublicKey):
        raise ManifestTamperedError("Public key is not Ed25519.")
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
    payload_hash = hashlib.sha256(payload).hexdigest()

    private_key = _load_private_key(private_path)
    public_key = _load_public_key(public_path)
    signature_bytes = private_key.sign(payload)

    signed = ManifestSignature(
        algorithm="ed25519",
        key_id=_public_key_id(public_key),
        payload_sha256=payload_hash,
        signature_b64=base64.b64encode(signature_bytes).decode("ascii"),
        signed_at=datetime.now(timezone.utc).isoformat(),
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
    payload_hash = hashlib.sha256(payload).hexdigest()

    public_key = _load_public_key(public_path)
    expected_key_id = _public_key_id(public_key)

    try:
        signature_data = json.loads(_read_bytes(signature).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestTamperedError("Manifest signature file is not valid JSON.") from exc

    required_fields = {"algorithm", "key_id", "payload_sha256", "signature", "signed_at"}
    if not required_fields.issubset(signature_data):
        raise ManifestTamperedError("Manifest signature file missing required fields.")

    if signature_data["algorithm"] != "ed25519":
        raise ManifestTamperedError("Unsupported manifest signature algorithm.")

    if signature_data["key_id"] != expected_key_id:
        raise ManifestTamperedError("Manifest signature key mismatch.")

    if signature_data["payload_sha256"] != payload_hash:
        raise ManifestTamperedError("Manifest hash mismatch; file has been modified.")

    try:
        signature_bytes = base64.b64decode(signature_data["signature"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ManifestTamperedError("Manifest signature encoding is invalid.") from exc

    try:
        public_key.verify(signature_bytes, payload)
    except Exception as exc:  # nosec B110 - explicit conversion to policy error
        raise ManifestTamperedError("Manifest signature verification failed.") from exc
