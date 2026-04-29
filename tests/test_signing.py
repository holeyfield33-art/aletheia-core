"""Tests for manifest/signing.py — Ed25519 keypair generation, sign, and verify."""

from __future__ import annotations

import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

from manifest.signing import (
    ManifestTamperedError,
    generate_keypair,
    sign_manifest,
    verify_manifest_signature,
)


def _tmp_dir():
    """Return a fresh temporary directory as a Path."""
    d = tempfile.mkdtemp()
    return Path(d)


def _write_manifest(
    directory: Path,
    content: str = '{"policy": "v1", "version": "1.0", "expires_at": "2099-01-01T00:00:00+00:00"}',
) -> Path:
    p = directory / "policy.json"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# generate_keypair
# ---------------------------------------------------------------------------


class TestGenerateKeypair(unittest.TestCase):
    def test_creates_private_key_file(self) -> None:
        d = _tmp_dir()
        generate_keypair(d / "priv.key", d / "pub.key")
        self.assertTrue((d / "priv.key").exists())

    def test_creates_public_key_file(self) -> None:
        d = _tmp_dir()
        generate_keypair(d / "priv.key", d / "pub.key")
        self.assertTrue((d / "pub.key").exists())

    def test_private_key_is_pem_encoded(self) -> None:
        d = _tmp_dir()
        generate_keypair(d / "priv.key", d / "pub.key")
        data = (d / "priv.key").read_bytes()
        self.assertIn(b"PRIVATE KEY", data)

    def test_public_key_is_pem_encoded(self) -> None:
        d = _tmp_dir()
        generate_keypair(d / "priv.key", d / "pub.key")
        data = (d / "pub.key").read_bytes()
        self.assertIn(b"PUBLIC KEY", data)

    def test_private_key_permissions_are_600(self) -> None:
        d = _tmp_dir()
        priv = d / "priv.key"
        generate_keypair(priv, d / "pub.key")
        mode = oct(os.stat(priv).st_mode & 0o777)
        self.assertEqual(mode, oct(0o600))

    def test_each_call_produces_different_keypair(self) -> None:
        d = _tmp_dir()
        generate_keypair(d / "priv1.key", d / "pub1.key")
        generate_keypair(d / "priv2.key", d / "pub2.key")
        self.assertNotEqual(
            (d / "pub1.key").read_bytes(),
            (d / "pub2.key").read_bytes(),
        )

    def test_creates_parent_directories(self) -> None:
        d = _tmp_dir()
        nested = d / "sub" / "dir"
        generate_keypair(nested / "priv.key", nested / "pub.key")
        self.assertTrue((nested / "priv.key").exists())


# ---------------------------------------------------------------------------
# sign_manifest
# ---------------------------------------------------------------------------


class TestSignManifest(unittest.TestCase):
    def _setup(self):
        d = _tmp_dir()
        manifest = _write_manifest(d)
        priv = d / "priv.key"
        pub = d / "pub.key"
        sig = d / "policy.json.sig"
        generate_keypair(priv, pub)
        return d, manifest, priv, pub, sig

    def test_sign_creates_signature_file(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        sign_manifest(manifest, sig, priv, pub)
        self.assertTrue(sig.exists())

    def test_signature_file_is_valid_json(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        sign_manifest(manifest, sig, priv, pub)
        data = json.loads(sig.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)

    def test_signature_file_contains_required_fields(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        sign_manifest(manifest, sig, priv, pub)
        data = json.loads(sig.read_text(encoding="utf-8"))
        for field in (
            "algorithm",
            "key_id",
            "payload_sha256",
            "signature",
            "signed_at",
        ):
            self.assertIn(field, data, f"Missing field: {field}")

    def test_algorithm_is_ed25519(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        sign_manifest(manifest, sig, priv, pub)
        data = json.loads(sig.read_text(encoding="utf-8"))
        self.assertEqual(data["algorithm"], "ed25519")

    def test_signature_is_base64_decodable(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        sign_manifest(manifest, sig, priv, pub)
        data = json.loads(sig.read_text(encoding="utf-8"))
        decoded = base64.b64decode(data["signature"], validate=True)
        self.assertEqual(len(decoded), 64)  # Ed25519 signatures are always 64 bytes

    def test_sign_generates_keys_if_missing(self) -> None:
        """sign_manifest auto-generates a keypair when key files are absent."""
        d = _tmp_dir()
        manifest = _write_manifest(d)
        priv = d / "auto_priv.key"
        pub = d / "auto_pub.key"
        sig = d / "policy.json.sig"
        # Keys do not exist yet
        self.assertFalse(priv.exists())
        sign_manifest(manifest, sig, priv, pub)
        self.assertTrue(sig.exists())
        self.assertTrue(priv.exists())
        self.assertTrue(pub.exists())

    def test_sign_returns_signature_path(self) -> None:
        d, manifest, priv, pub, sig = self._setup()
        returned = sign_manifest(manifest, sig, priv, pub)
        self.assertEqual(Path(returned), sig)


# ---------------------------------------------------------------------------
# verify_manifest_signature
# ---------------------------------------------------------------------------


class TestVerifyManifestSignature(unittest.TestCase):
    def _signed_setup(self, content: str = '{"policy": "v1"}'):
        if content == '{"policy": "v1"}':
            content = '{"policy": "v1", "version": "1.0", "expires_at": "2099-01-01T00:00:00+00:00"}'
        d = _tmp_dir()
        manifest = _write_manifest(d, content)
        priv = d / "priv.key"
        pub = d / "pub.key"
        sig = d / "policy.json.sig"
        generate_keypair(priv, pub)
        sign_manifest(manifest, sig, priv, pub)
        return d, manifest, priv, pub, sig

    def test_valid_signature_does_not_raise(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        # Should complete without raising
        verify_manifest_signature(manifest, sig, pub)

    def test_tampered_manifest_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        # Modify manifest after signing
        manifest.write_text(
            '{"policy": "tampered", "version": "1.0", "expires_at": "2099-01-01T00:00:00+00:00"}',
            encoding="utf-8",
        )
        with self.assertRaises(ManifestTamperedError) as ctx:
            verify_manifest_signature(manifest, sig, pub)
        self.assertIn("hash mismatch", str(ctx.exception).lower())

    def test_missing_manifest_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        manifest.unlink()
        with self.assertRaises(ManifestTamperedError) as ctx:
            verify_manifest_signature(manifest, sig, pub)
        self.assertIn("missing", str(ctx.exception).lower())

    def test_missing_signature_file_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        sig.unlink()
        with self.assertRaises(ManifestTamperedError):
            verify_manifest_signature(manifest, sig, pub)

    def test_missing_public_key_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        pub.unlink()
        with self.assertRaises(ManifestTamperedError):
            verify_manifest_signature(manifest, sig, pub)

    def test_wrong_key_raises(self) -> None:
        """Verifying with a different public key should fail."""
        d, manifest, priv, pub, sig = self._signed_setup()
        # Generate a second (unrelated) keypair
        priv2 = d / "priv2.key"
        pub2 = d / "pub2.key"
        generate_keypair(priv2, pub2)
        with self.assertRaises(ManifestTamperedError):
            verify_manifest_signature(manifest, sig, pub2)

    def test_corrupted_signature_bytes_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        data = json.loads(sig.read_text(encoding="utf-8"))
        # Flip a byte in the signature
        raw = base64.b64decode(data["signature"])
        corrupted = bytes([raw[0] ^ 0xFF]) + raw[1:]
        data["signature"] = base64.b64encode(corrupted).decode("ascii")
        sig.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ManifestTamperedError):
            verify_manifest_signature(manifest, sig, pub)

    def test_invalid_json_signature_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        sig.write_text("not json at all", encoding="utf-8")
        with self.assertRaises(ManifestTamperedError) as ctx:
            verify_manifest_signature(manifest, sig, pub)
        self.assertIn("not valid json", str(ctx.exception).lower())

    def test_missing_fields_in_signature_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        # Write a JSON object missing required fields
        sig.write_text(json.dumps({"algorithm": "ed25519"}), encoding="utf-8")
        with self.assertRaises(ManifestTamperedError) as ctx:
            verify_manifest_signature(manifest, sig, pub)
        self.assertIn("missing required fields", str(ctx.exception).lower())

    def test_wrong_algorithm_raises(self) -> None:
        d, manifest, priv, pub, sig = self._signed_setup()
        data = json.loads(sig.read_text(encoding="utf-8"))
        data["algorithm"] = "rsa"
        sig.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ManifestTamperedError) as ctx:
            verify_manifest_signature(manifest, sig, pub)
        self.assertIn("unsupported", str(ctx.exception).lower())

    def test_sign_verify_roundtrip_with_binary_content(self) -> None:
        """Signing works for manifests with unicode/special characters."""
        d = _tmp_dir()
        content = json.dumps(
            {
                "policy": "v1",
                "note": "caf\u00e9 \u4e2d\u6587",
                "version": "1.0",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }
        )
        manifest = _write_manifest(d, content)
        priv = d / "priv.key"
        pub = d / "pub.key"
        sig = d / "policy.json.sig"
        generate_keypair(priv, pub)
        sign_manifest(manifest, sig, priv, pub)
        # Should not raise
        verify_manifest_signature(manifest, sig, pub)


if __name__ == "__main__":
    unittest.main()
