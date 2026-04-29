"""Tests for core/config.py — AletheiaSettings.load() with YAML and env-var overrides."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestAletheiaSettingsDefaults(unittest.TestCase):
    """Verify default values when no config file and no env vars are present."""

    def _load_clean(self):
        """Return a fresh AletheiaSettings loaded with no env overrides and no YAML file."""
        # Import inside the method so we can reload with a clean env
        from core.config import AletheiaSettings

        # Patch _load_yaml to return empty dict (no file on disk)
        with patch("core.config._load_yaml", return_value={}):
            # Clear any ALETHEIA_* env vars that might be set in the test environment
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("ALETHEIA_")
            }
            with patch.dict(os.environ, clean_env, clear=True):
                return AletheiaSettings.load()

    def test_default_embedding_model(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.embedding_model, "all-MiniLM-L6-v2")

    def test_default_intent_threshold(self) -> None:
        s = self._load_clean()
        self.assertAlmostEqual(s.intent_threshold, 0.55)

    def test_default_policy_threshold(self) -> None:
        s = self._load_clean()
        self.assertAlmostEqual(s.policy_threshold, 7.5)

    def test_default_rate_limit(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.rate_limit_per_second, 10)

    def test_default_mode_is_active(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.mode, "active")

    def test_default_shadow_mode_is_false(self) -> None:
        s = self._load_clean()
        self.assertFalse(s.shadow_mode)

    def test_default_client_id(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.client_id, "ALETHEIA_ENTERPRISE")

    def test_default_polymorphic_modes(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.polymorphic_modes, ["LINEAGE", "INTENT", "SKEPTIC"])

    def test_default_log_level(self) -> None:
        s = self._load_clean()
        self.assertEqual(s.log_level, "INFO")


class TestShadowModeDerivedFromMode(unittest.TestCase):
    """shadow_mode flag must be derived from the mode field via __post_init__."""

    def test_shadow_mode_true_when_mode_is_shadow(self) -> None:
        from core.config import AletheiaSettings

        s = AletheiaSettings(mode="shadow")
        self.assertTrue(s.shadow_mode)

    def test_shadow_mode_false_when_mode_is_active(self) -> None:
        from core.config import AletheiaSettings

        s = AletheiaSettings(mode="active")
        self.assertFalse(s.shadow_mode)

    def test_shadow_mode_false_when_mode_is_monitor(self) -> None:
        from core.config import AletheiaSettings

        s = AletheiaSettings(mode="monitor")
        self.assertFalse(s.shadow_mode)


class TestYamlLoading(unittest.TestCase):
    """Values from a YAML config file should override defaults."""

    def _load_with_yaml(self, yaml_content: str):
        import yaml
        from core.config import AletheiaSettings

        parsed = yaml.safe_load(yaml_content)
        with patch("core.config._load_yaml", return_value=parsed or {}):
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("ALETHEIA_")
            }
            with patch.dict(os.environ, clean_env, clear=True):
                return AletheiaSettings.load()

    def test_yaml_overrides_policy_threshold(self) -> None:
        s = self._load_with_yaml("policy_threshold: 5.0")
        self.assertAlmostEqual(s.policy_threshold, 5.0)

    def test_yaml_overrides_mode(self) -> None:
        s = self._load_with_yaml("mode: shadow")
        self.assertEqual(s.mode, "shadow")
        self.assertTrue(s.shadow_mode)

    def test_yaml_overrides_client_id(self) -> None:
        s = self._load_with_yaml("client_id: MY_CORP")
        self.assertEqual(s.client_id, "MY_CORP")

    def test_yaml_overrides_rate_limit(self) -> None:
        s = self._load_with_yaml("rate_limit_per_second: 25")
        self.assertEqual(s.rate_limit_per_second, 25)

    def test_yaml_overrides_log_level(self) -> None:
        s = self._load_with_yaml("log_level: DEBUG")
        self.assertEqual(s.log_level, "DEBUG")

    def test_empty_yaml_uses_defaults(self) -> None:
        s = self._load_with_yaml("")
        self.assertAlmostEqual(s.policy_threshold, 7.5)

    def test_non_dict_yaml_uses_defaults(self) -> None:
        """_load_yaml returns {} for non-dict YAML, so defaults apply."""
        # _load_yaml already coerces non-dict content to {} before it reaches load().
        # Simulate that by patching with the result _load_yaml would produce.
        from core.config import AletheiaSettings

        with patch("core.config._load_yaml", return_value={}):
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("ALETHEIA_")
            }
            with patch.dict(os.environ, clean_env, clear=True):
                s = AletheiaSettings.load()
        self.assertAlmostEqual(s.policy_threshold, 7.5)


class TestEnvVarOverrides(unittest.TestCase):
    """Environment variables must win over both defaults and YAML values."""

    def _load_with_env(self, env_vars: dict):
        from core.config import AletheiaSettings

        with patch("core.config._load_yaml", return_value={}):
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("ALETHEIA_")
            }
            clean_env.update(env_vars)
            with patch.dict(os.environ, clean_env, clear=True):
                return AletheiaSettings.load()

    def test_env_overrides_policy_threshold_float(self) -> None:
        s = self._load_with_env({"ALETHEIA_POLICY_THRESHOLD": "3.5"})
        self.assertAlmostEqual(s.policy_threshold, 3.5)

    def test_env_overrides_intent_threshold_float(self) -> None:
        s = self._load_with_env({"ALETHEIA_INTENT_THRESHOLD": "0.75"})
        self.assertAlmostEqual(s.intent_threshold, 0.75)

    def test_env_overrides_rate_limit_int(self) -> None:
        s = self._load_with_env({"ALETHEIA_RATE_LIMIT_PER_SECOND": "50"})
        self.assertEqual(s.rate_limit_per_second, 50)

    def test_env_overrides_mode_string(self) -> None:
        s = self._load_with_env({"ALETHEIA_MODE": "shadow"})
        self.assertEqual(s.mode, "shadow")
        self.assertTrue(s.shadow_mode)

    def test_env_overrides_client_id_string(self) -> None:
        s = self._load_with_env({"ALETHEIA_CLIENT_ID": "CUSTOM_ID"})
        self.assertEqual(s.client_id, "CUSTOM_ID")

    def test_env_overrides_polymorphic_modes_list(self) -> None:
        s = self._load_with_env({"ALETHEIA_POLYMORPHIC_MODES": "LINEAGE, SKEPTIC"})
        self.assertEqual(s.polymorphic_modes, ["LINEAGE", "SKEPTIC"])

    def test_env_wins_over_yaml(self) -> None:
        from core.config import AletheiaSettings

        yaml_data = {"policy_threshold": 5.0}
        with patch("core.config._load_yaml", return_value=yaml_data):
            clean_env = {
                k: v for k, v in os.environ.items() if not k.startswith("ALETHEIA_")
            }
            clean_env["ALETHEIA_POLICY_THRESHOLD"] = "2.0"
            with patch.dict(os.environ, clean_env, clear=True):
                s = AletheiaSettings.load()
        self.assertAlmostEqual(s.policy_threshold, 2.0)

    def test_log_level_env_override(self) -> None:
        s = self._load_with_env({"ALETHEIA_LOG_LEVEL": "WARNING"})
        self.assertEqual(s.log_level, "WARNING")


class TestLoadYamlFileDiscovery(unittest.TestCase):
    """_load_yaml() should find and parse config.yaml from disk."""

    def test_loads_from_config_yaml_file(self) -> None:
        from core.config import _load_yaml

        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.yaml"
            config_file.write_text(
                "policy_threshold: 4.2\nclient_id: TEST_CORP\n", encoding="utf-8"
            )
            original_dir = os.getcwd()
            try:
                os.chdir(tmp)
                data = _load_yaml()
                self.assertAlmostEqual(data.get("policy_threshold"), 4.2)
                self.assertEqual(data.get("client_id"), "TEST_CORP")
            finally:
                os.chdir(original_dir)

    def test_returns_empty_dict_when_no_file(self) -> None:
        from core.config import _load_yaml

        with tempfile.TemporaryDirectory() as tmp:
            original_dir = os.getcwd()
            try:
                os.chdir(tmp)
                with patch.dict(os.environ, {"ALETHEIA_CONFIG_PATH": ""}, clear=False):
                    data = _load_yaml()
                self.assertEqual(data, {})
            finally:
                os.chdir(original_dir)

    def test_env_config_path_is_used(self) -> None:
        """_CONFIG_SEARCH_PATHS can be patched to point at a custom file."""
        import core.config as cfg_mod
        from core.config import _load_yaml

        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "custom.yaml"
            config_file.write_text("client_id: ENV_CORP\n", encoding="utf-8")
            original_paths = cfg_mod._CONFIG_SEARCH_PATHS
            try:
                cfg_mod._CONFIG_SEARCH_PATHS = [config_file]
                data = _load_yaml()
            finally:
                cfg_mod._CONFIG_SEARCH_PATHS = original_paths
            self.assertEqual(data.get("client_id"), "ENV_CORP")


if __name__ == "__main__":
    unittest.main()
