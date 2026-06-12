"""Tests for manifest expiry validation with 7-day grace period.

Verifies that signing.py correctly handles:
- Valid (non-expired) manifests → accepted
- Recently expired manifests (within grace) → accepted with warning
- Expired beyond grace period → hard rejection
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from manifest.signing import (
    generate_keypair,
    sign_manifest,
    verify_manifest_signature,
    ManifestTamperedError,
    _GRACE_PERIOD_DAYS,
)


def _create_manifest(
    tmp_dir: str, expires_at: str, version: str = "test.1"
) -> dict[str, Path]:
    """Create a test manifest with a specific expiry and sign it."""
    manifest_path = Path(tmp_dir) / "policy.json"
    sig_path = Path(tmp_dir) / "policy.json.sig"
    priv_path = Path(tmp_dir) / "test.pem"
    pub_path = Path(tmp_dir) / "test.pub"

    policy = {
        "policy_name": "Test_Policy",
        "version": version,
        "expires_at": expires_at,
        "enforcement_level": "HARD_VETO",
        "restricted_actions": [],
        "approval_protocol": "DUAL_KEY_REQUIRED",
        "signatories": ["TEST"],
    }
    manifest_path.write_text(json.dumps(policy), encoding="utf-8")

    generate_keypair(priv_path, pub_path)
    sign_manifest(manifest_path, sig_path, priv_path, pub_path)

    return {
        "manifest": manifest_path,
        "signature": sig_path,
        "public_key": pub_path,
    }


class TestManifestExpiry(unittest.TestCase):
    def test_valid_manifest_accepted(self):
        """Manifest expiring in the future is accepted."""
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            paths = _create_manifest(tmp, future)
            # Should not raise
            verify_manifest_signature(
                paths["manifest"], paths["signature"], paths["public_key"]
            )

    @mock.patch.dict(os.environ, {"ALETHEIA_MANIFEST_GRACE_DAYS": "7"})
    def test_recently_expired_within_grace_accepted(self):
        """Manifest expired 3 days ago (within an explicit 7-day grace) is accepted."""
        expired = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            paths = _create_manifest(tmp, expired)
            # Should NOT raise — within grace period
            verify_manifest_signature(
                paths["manifest"], paths["signature"], paths["public_key"]
            )

    @mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False)
    def test_production_default_rejects_recently_expired(self):
        """Fail-closed: in production the grace defaults to 0, so a manifest
        expired even 1 day ago is hard-rejected without an explicit override."""
        os.environ.pop("ALETHEIA_MANIFEST_GRACE_DAYS", None)
        expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            paths = _create_manifest(tmp, expired)
            with self.assertRaises(ManifestTamperedError) as ctx:
                verify_manifest_signature(
                    paths["manifest"], paths["signature"], paths["public_key"]
                )
            self.assertIn("grace period", str(ctx.exception).lower())

    def test_expired_beyond_grace_rejected(self):
        """Manifest expired > 7 days ago is hard-rejected."""
        expired = (
            datetime.now(timezone.utc) - timedelta(days=_GRACE_PERIOD_DAYS + 1)
        ).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            paths = _create_manifest(tmp, expired)
            with self.assertRaises(ManifestTamperedError) as ctx:
                verify_manifest_signature(
                    paths["manifest"], paths["signature"], paths["public_key"]
                )
            self.assertIn("grace period", str(ctx.exception).lower())

    def test_grace_period_is_seven_days(self):
        self.assertEqual(_GRACE_PERIOD_DAYS, 7)

    @mock.patch.dict(os.environ, {"ALETHEIA_MANIFEST_GRACE_DAYS": "7"})
    def test_expired_exactly_at_grace_boundary(self):
        """Manifest expired 6 days ago — safely within an explicit 7-day grace."""
        expired = (
            datetime.now(timezone.utc) - timedelta(days=_GRACE_PERIOD_DAYS - 1)
        ).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            paths = _create_manifest(tmp, expired)
            # 6 days < 7-day grace period → accepted
            verify_manifest_signature(
                paths["manifest"], paths["signature"], paths["public_key"]
            )


if __name__ == "__main__":
    unittest.main()
