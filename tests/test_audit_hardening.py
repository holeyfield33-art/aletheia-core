"""Tests for the audit-hardening controls added from the security review.

Covers:
- Fail-closed environment detection (is_production_environment)
- Opaque-decision gating (opaque_decisions_enabled)
- Production-config checks for HMAC-only receipts and an unpinned manifest key
- Manifest signing rejects a public key that does not match the pinned
  ALETHEIA_MANIFEST_EXPECTED_KEY_ID fingerprint
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from core.config import is_production_environment, opaque_decisions_enabled
from manifest.signing import (
    ManifestTamperedError,
    _public_key_id,
    _load_public_key,
    generate_keypair,
    sign_manifest,
    verify_manifest_signature,
)


class TestEnvironmentFailClosed(unittest.TestCase):
    @mock.patch.dict(os.environ, {}, clear=True)
    def test_unset_environment_is_production(self):
        self.assertTrue(is_production_environment())

    @mock.patch.dict(os.environ, {"ENVIRONMENT": "Production"}, clear=True)
    def test_misspelled_environment_is_production(self):
        # Anything not in the explicit dev set is treated as production.
        self.assertTrue(is_production_environment())

    @mock.patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True)
    def test_staging_is_production(self):
        self.assertTrue(is_production_environment())

    def test_dev_values_are_not_production(self):
        for env in ("development", "dev", "test", "testing", "local"):
            with mock.patch.dict(os.environ, {"ENVIRONMENT": env}, clear=True):
                self.assertFalse(is_production_environment(), env)


class TestOpaqueDecisions(unittest.TestCase):
    @mock.patch.dict(os.environ, {"ENVIRONMENT": "dev"}, clear=True)
    def test_default_off_in_dev(self):
        self.assertFalse(opaque_decisions_enabled())

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_default_on_in_production(self):
        self.assertTrue(opaque_decisions_enabled())

    @mock.patch.dict(
        os.environ,
        {"ENVIRONMENT": "production", "ALETHEIA_OPAQUE_DECISIONS": "false"},
        clear=True,
    )
    def test_explicit_off_overrides_production(self):
        self.assertFalse(opaque_decisions_enabled())

    @mock.patch.dict(
        os.environ,
        {"ENVIRONMENT": "dev", "ALETHEIA_OPAQUE_DECISIONS": "true"},
        clear=True,
    )
    def test_explicit_on_overrides_dev(self):
        self.assertTrue(opaque_decisions_enabled())


class TestProductionConfigChecks(unittest.TestCase):
    """Exercise the new HMAC-receipt and manifest-key-pin advisories."""

    def _run(self, env: dict[str, str]) -> list[str]:
        # Re-import inside a patched env so settings reflect the scenario.
        import importlib

        import core.config as cfg

        with mock.patch.dict(os.environ, env, clear=True):
            importlib.reload(cfg)
            try:
                return cfg.validate_production_config()
            finally:
                # Restore the module singleton for other tests.
                importlib.reload(cfg)

    def test_flags_hmac_only_receipts(self):
        issues = self._run(
            {
                "ALETHEIA_RECEIPT_SECRET": "x" * 40,
                "ALETHEIA_REQUIRE_ED25519_RECEIPTS": "false",
                "ALETHEIA_ALLOW_SQLITE_PRODUCTION": "true",
                "ALETHEIA_ALLOW_ENV_SECRETS": "true",
                "REDIS_URL": "rediss://localhost:6379",
                "ALETHEIA_MANIFEST_EXPECTED_KEY_ID": "deadbeef",
            }
        )
        joined = "\n".join(issues)
        self.assertIn("HMAC-SHA256 only", joined)

    def test_hmac_acknowledgement_suppresses_flag(self):
        issues = self._run(
            {
                "ALETHEIA_RECEIPT_SECRET": "x" * 40,
                "ALETHEIA_ALLOW_HMAC_RECEIPTS": "true",
                "ALETHEIA_ALLOW_SQLITE_PRODUCTION": "true",
                "ALETHEIA_ALLOW_ENV_SECRETS": "true",
                "REDIS_URL": "rediss://localhost:6379",
                "ALETHEIA_MANIFEST_EXPECTED_KEY_ID": "deadbeef",
            }
        )
        self.assertNotIn("HMAC-SHA256 only", "\n".join(issues))

    def test_flags_unpinned_manifest_key(self):
        issues = self._run(
            {
                "ALETHEIA_RECEIPT_SECRET": "x" * 40,
                "ALETHEIA_ALLOW_HMAC_RECEIPTS": "true",
                "ALETHEIA_ALLOW_SQLITE_PRODUCTION": "true",
                "ALETHEIA_ALLOW_ENV_SECRETS": "true",
                "REDIS_URL": "rediss://localhost:6379",
            }
        )
        self.assertIn("ALETHEIA_MANIFEST_EXPECTED_KEY_ID", "\n".join(issues))


class TestManifestKeyPin(unittest.TestCase):
    def _make_signed_manifest(self, tmp: str) -> dict[str, Path]:
        manifest_path = Path(tmp) / "policy.json"
        sig_path = Path(tmp) / "policy.json.sig"
        priv_path = Path(tmp) / "test.pem"
        pub_path = Path(tmp) / "test.pub"
        policy = {
            "policy_name": "Test_Policy",
            "version": "test.1",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat(),
            "enforcement_level": "HARD_VETO",
            "restricted_actions": [],
            "approval_protocol": "DUAL_KEY_REQUIRED",
            "signatories": ["TEST"],
        }
        manifest_path.write_text(json.dumps(policy), encoding="utf-8")
        generate_keypair(priv_path, pub_path)
        sign_manifest(manifest_path, sig_path, priv_path, pub_path)
        return {"manifest": manifest_path, "signature": sig_path, "public_key": pub_path}

    def test_correct_pin_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._make_signed_manifest(tmp)
            real_id = _public_key_id(_load_public_key(paths["public_key"]))
            with mock.patch.dict(
                os.environ, {"ALETHEIA_MANIFEST_EXPECTED_KEY_ID": real_id}, clear=False
            ):
                verify_manifest_signature(
                    paths["manifest"], paths["signature"], paths["public_key"]
                )

    def test_wrong_pin_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._make_signed_manifest(tmp)
            with mock.patch.dict(
                os.environ,
                {"ALETHEIA_MANIFEST_EXPECTED_KEY_ID": "00" * 32},
                clear=False,
            ):
                with self.assertRaises(ManifestTamperedError) as ctx:
                    verify_manifest_signature(
                        paths["manifest"], paths["signature"], paths["public_key"]
                    )
                self.assertIn("pinned", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
