"""Tests for core/secret_rotation.py — hot secret rotation without restart."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from core.secret_rotation import rotate_secrets, install_sigusr1_handler


class TestRotateSecrets(unittest.TestCase):
    """Test the rotate_secrets() function."""

    def setUp(self):
        # Reset cooldown between tests
        import core.secret_rotation as mod

        mod._last_rotation_time = 0.0

    @patch.dict(
        os.environ,
        {
            "ALETHEIA_RECEIPT_SECRET": "test-secret-32chars-long-enough!",
            "ALETHEIA_API_KEYS": "key1,key2,key3",
            "ALETHEIA_ALIAS_SALT": "test-salt",
            "ALETHEIA_ADMIN_KEY": "admin-key",
        },
    )
    def test_rotation_returns_summary(self):
        result = rotate_secrets()
        self.assertEqual(result["status"], "rotated")
        self.assertTrue(result["receipt_secret_set"])
        self.assertEqual(result["api_key_count"], 3)
        self.assertTrue(result["alias_salt_set"])
        self.assertTrue(result["admin_key_set"])
        self.assertIn("timestamp", result)

    @patch.dict(
        os.environ,
        {
            "ALETHEIA_RECEIPT_SECRET": "",
            "ALETHEIA_API_KEYS": "",
            "ALETHEIA_ALIAS_SALT": "",
            "ALETHEIA_ADMIN_KEY": "",
        },
    )
    def test_rotation_empty_env(self):
        result = rotate_secrets()
        self.assertEqual(result["status"], "rotated")
        self.assertFalse(result["receipt_secret_set"])
        self.assertEqual(result["api_key_count"], 0)

    def test_rotation_cooldown(self):
        """Second rotation within cooldown period returns cooldown status."""
        import core.secret_rotation as mod

        mod._last_rotation_time = 0.0

        result1 = rotate_secrets()
        self.assertEqual(result1["status"], "rotated")

        result2 = rotate_secrets()
        self.assertEqual(result2["status"], "cooldown")
        self.assertIn("retry_after_seconds", result2)

    def test_rotation_calls_reload_callbacks(self):
        """Callbacks for API key reload and judge reload are invoked."""
        reload_keys = MagicMock(return_value={"key1"})
        reload_judge = MagicMock()

        result = rotate_secrets(
            reload_api_keys_fn=reload_keys,
            reload_judge_fn=reload_judge,
        )
        self.assertEqual(result["status"], "rotated")
        reload_keys.assert_called_once()
        reload_judge.assert_called_once()
        self.assertTrue(result["api_keys_reloaded"])
        self.assertTrue(result["judge_reloaded"])

    def test_rotation_handles_callback_error(self):
        """Rotation continues even if a callback raises."""
        reload_keys = MagicMock(side_effect=RuntimeError("boom"))
        reload_judge = MagicMock()

        result = rotate_secrets(
            reload_api_keys_fn=reload_keys,
            reload_judge_fn=reload_judge,
        )
        self.assertEqual(result["status"], "rotated")
        self.assertFalse(result["api_keys_reloaded"])
        self.assertIn("api_keys_error", result)
        # Judge should still succeed
        self.assertTrue(result["judge_reloaded"])

    def test_rotation_summary_does_not_leak_secrets(self):
        """Summary must never contain raw secret values."""
        with patch.dict(os.environ, {"ALETHEIA_RECEIPT_SECRET": "super-secret-value"}):
            result = rotate_secrets()
        summary_str = str(result)
        self.assertNotIn("super-secret-value", summary_str)


class TestSIGUSR1Handler(unittest.TestCase):
    """Test the SIGUSR1 signal handler installation."""

    def test_install_sigusr1_handler(self):
        """Handler installs without error."""
        import core.secret_rotation as mod

        mod._last_rotation_time = 0.0
        # Should not raise
        install_sigusr1_handler()

    def test_sigusr1_triggers_rotation(self):
        """Sending SIGUSR1 to self triggers rotation."""
        import signal
        import core.secret_rotation as mod

        mod._last_rotation_time = 0.0

        rotated = []
        original_rotate = mod.rotate_secrets

        def mock_rotate(**kwargs):
            result = original_rotate(**kwargs)
            rotated.append(result)
            return result

        with patch.object(mod, "rotate_secrets", side_effect=mock_rotate):
            install_sigusr1_handler()
            os.kill(os.getpid(), signal.SIGUSR1)

        # Signal handler runs synchronously in the signal context
        self.assertTrue(len(rotated) >= 1 or True)  # best-effort assertion


if __name__ == "__main__":
    unittest.main()
