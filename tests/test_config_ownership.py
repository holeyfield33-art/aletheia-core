"""Tests for config ownership validation in core/config.py."""
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestConfigOwnershipValidation(unittest.TestCase):
    """Validate that world/group-writable config files are rejected."""

    def test_owned_config_accepted(self):
        """Config file owned by current user with safe permissions passes."""
        from core.config import _validate_config_ownership
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"mode: shadow\n")
            f.flush()
            path = Path(f.name)
        try:
            os.chmod(path, 0o600)
            # Should not raise — owned by current user
            _validate_config_ownership(path)
        finally:
            path.unlink()

    def test_group_writable_foreign_config_rejected(self):
        """Config file writable by group and owned by other raises PermissionError."""
        from core.config import _validate_config_ownership
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"mode: active\n")
            f.flush()
            path = Path(f.name)
        try:
            os.chmod(path, 0o664)
            # Simulate foreign ownership by patching os.getuid
            with patch("os.getuid", return_value=99999):
                with self.assertRaises(PermissionError):
                    _validate_config_ownership(path)
        finally:
            path.unlink()

    def test_world_writable_foreign_config_rejected(self):
        """Config owned by another with world-write bit raises."""
        from core.config import _validate_config_ownership
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"mode: active\n")
            f.flush()
            path = Path(f.name)
        try:
            os.chmod(path, 0o666)
            with patch("os.getuid", return_value=99999):
                with self.assertRaises(PermissionError):
                    _validate_config_ownership(path)
        finally:
            path.unlink()

    def test_owner_writable_config_accepted(self):
        """Config writable by owner (same uid) is accepted regardless of group/world bits."""
        from core.config import _validate_config_ownership
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            f.write(b"mode: active\n")
            f.flush()
            path = Path(f.name)
        try:
            os.chmod(path, 0o644)
            # Same uid — should pass even with group-readable
            _validate_config_ownership(path)
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
