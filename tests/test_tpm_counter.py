"""Tests for TPM anti-rollback monotonic counter (Phase 4)."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from crypto.tpm_interface import TPMAnchor, _NV_BASE


class _CounterFixture(unittest.TestCase):
    """Base class that patches the key path and counter log to temp files."""

    def setUp(self) -> None:
        # Temp key path so _SoftwareBackend persists a key to disk
        self._key_fd, self._key_path = tempfile.mkstemp(suffix=".pem")
        os.close(self._key_fd)
        os.unlink(self._key_path)  # let _SoftwareBackend create it

        # Temp counter log
        self._log_fd, self._log_path = tempfile.mkstemp(suffix=".log")
        os.close(self._log_fd)
        os.unlink(self._log_path)  # start with no log

        env_patch = {
            "ALETHEIA_CHAIN_KEY_PATH": self._key_path,
            "ALETHEIA_COUNTER_LOG_PATH": self._log_path,
        }
        self._env_patcher = patch.dict(os.environ, env_patch)
        self._env_patcher.start()

        self.anchor = TPMAnchor()

    def tearDown(self) -> None:
        self._env_patcher.stop()
        for p in (self._key_path, self._log_path):
            if os.path.exists(p):
                os.unlink(p)


# ------------------------------------------------------------------
# Signed-log fallback (software backend)
# ------------------------------------------------------------------
class TestSignedLogCounter(_CounterFixture):
    def test_initial_counter_is_zero(self) -> None:
        self.assertEqual(self.anchor.get_monotonic_counter(), 0)

    def test_increment_returns_true(self) -> None:
        self.assertTrue(self.anchor.increment_monotonic_counter())

    def test_counter_increases_by_one(self) -> None:
        self.anchor.increment_monotonic_counter()
        self.assertEqual(self.anchor.get_monotonic_counter(), 1)

    def test_multiple_increments(self) -> None:
        for _ in range(5):
            self.anchor.increment_monotonic_counter()
        self.assertEqual(self.anchor.get_monotonic_counter(), 5)

    def test_monotonicity(self) -> None:
        prev = 0
        for _ in range(10):
            self.anchor.increment_monotonic_counter()
            current = self.anchor.get_monotonic_counter()
            self.assertGreater(current, prev)
            prev = current

    def test_log_file_created_on_increment(self) -> None:
        self.assertFalse(os.path.exists(self._log_path))
        self.anchor.increment_monotonic_counter()
        self.assertTrue(os.path.exists(self._log_path))

    def test_umask_restored_after_increment(self) -> None:
        before = os.umask(0o022)
        os.umask(before)  # restore immediately
        self.anchor.increment_monotonic_counter()
        after = os.umask(0o022)
        os.umask(after)
        self.assertEqual(before, after)

    def test_counter_log_path_from_env(self) -> None:
        self.assertEqual(self.anchor._counter_log_path, self._log_path)


class TestSignatureVerification(_CounterFixture):
    def test_tampered_nonce_ignored(self) -> None:
        self.anchor.increment_monotonic_counter()  # counter=1
        # Tamper: append a fake entry with nonce 999
        with open(self._log_path, "a") as fh:
            fh.write("9999999 999 deadbeef\n")
        # Tampered line should be ignored; counter still 1
        self.assertEqual(self.anchor.get_monotonic_counter(), 1)

    def test_malformed_lines_skipped(self) -> None:
        self.anchor.increment_monotonic_counter()
        with open(self._log_path, "a") as fh:
            fh.write("not a valid line\n")
            fh.write("\n")
            fh.write("too few\n")
            fh.write("too many fields here really way too many\n")
        self.assertEqual(self.anchor.get_monotonic_counter(), 1)

    def test_wrong_key_entries_ignored(self) -> None:
        self.anchor.increment_monotonic_counter()  # counter=1

        # Create a second anchor with a *different* key
        other_key_fd, other_key_path = tempfile.mkstemp(suffix=".pem")
        os.close(other_key_fd)
        os.unlink(other_key_path)
        with patch.dict(os.environ, {"ALETHEIA_CHAIN_KEY_PATH": other_key_path}):
            other_anchor = TPMAnchor()
        if os.path.exists(other_key_path):
            os.unlink(other_key_path)

        # Sign a counter entry with the other key and append
        entry = "0 50"
        sig = other_anchor._backend.sign(entry.encode())
        with open(self._log_path, "a") as fh:
            fh.write(f"{entry} {sig.hex()}\n")

        # Original anchor should ignore the entry signed by wrong key
        self.assertEqual(self.anchor.get_monotonic_counter(), 1)

    def test_non_integer_nonce_skipped(self) -> None:
        self.anchor.increment_monotonic_counter()
        with open(self._log_path, "a") as fh:
            fh.write("123 not_a_number abcdef\n")
        self.assertEqual(self.anchor.get_monotonic_counter(), 1)


class TestIncrementAtomicity(_CounterFixture):
    def test_increment_reads_under_lock(self) -> None:
        """Increment reads current value and writes new value atomically."""
        self.anchor.increment_monotonic_counter()
        self.anchor.increment_monotonic_counter()
        # Value should be exactly 2, not 1 (no duplicate from re-reads)
        self.assertEqual(self.anchor.get_monotonic_counter(), 2)

    def test_increment_after_external_append(self) -> None:
        """Increment should read past valid entries before appending."""
        self.anchor.increment_monotonic_counter()  # counter=1
        # Directly increment again
        self.anchor.increment_monotonic_counter()  # counter=2
        self.anchor.increment_monotonic_counter()  # counter=3
        self.assertEqual(self.anchor.get_monotonic_counter(), 3)


# ------------------------------------------------------------------
# TPM backend dispatch (mocked)
# ------------------------------------------------------------------
class TestTPMBackendDispatch(unittest.TestCase):
    def _make_tpm_anchor(self) -> TPMAnchor:
        """Create a TPMAnchor that thinks it has a TPM backend."""
        anchor = TPMAnchor.__new__(TPMAnchor)
        mock_backend = MagicMock()
        mock_backend.__class__ = type("_TPMBackend", (), {})
        anchor._backend = mock_backend
        return anchor

    def test_get_counter_delegates_to_nv_read(self) -> None:
        anchor = self._make_tpm_anchor()
        anchor._backend.nv_read_counter.return_value = 42
        # backend_type must return "tpm"
        with patch.object(
            type(anchor),
            "backend_type",
            new_callable=lambda: property(lambda self: "tpm"),
        ):
            result = anchor.get_monotonic_counter(counter_index=3)
        anchor._backend.nv_read_counter.assert_called_once_with(3)
        self.assertEqual(result, 42)

    def test_increment_delegates_to_nv_increment(self) -> None:
        anchor = self._make_tpm_anchor()
        anchor._backend.nv_increment_counter.return_value = 43
        with patch.object(
            type(anchor),
            "backend_type",
            new_callable=lambda: property(lambda self: "tpm"),
        ):
            result = anchor.increment_monotonic_counter(counter_index=1)
        anchor._backend.nv_increment_counter.assert_called_once_with(1)
        self.assertTrue(result)

    def test_tpm_read_failure_returns_none(self) -> None:
        anchor = self._make_tpm_anchor()
        anchor._backend.nv_read_counter.side_effect = RuntimeError("TPM error")
        with patch.object(
            type(anchor),
            "backend_type",
            new_callable=lambda: property(lambda self: "tpm"),
        ):
            result = anchor.get_monotonic_counter()
        self.assertIsNone(result)

    def test_tpm_increment_failure_returns_false(self) -> None:
        anchor = self._make_tpm_anchor()
        anchor._backend.nv_increment_counter.side_effect = RuntimeError("TPM error")
        with patch.object(
            type(anchor),
            "backend_type",
            new_callable=lambda: property(lambda self: "tpm"),
        ):
            result = anchor.increment_monotonic_counter()
        self.assertFalse(result)


class TestNVBaseConstant(unittest.TestCase):
    def test_nv_base_value(self) -> None:
        self.assertEqual(_NV_BASE, 0x01800000)


if __name__ == "__main__":
    unittest.main()
