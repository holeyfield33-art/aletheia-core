"""Tests for bridge/config.py — AletheiaConfig legacy facade.

Previously zero test coverage. These tests verify:
- AletheiaConfig class attributes exist and have correct types
- Attribute values reflect core.config.settings at import time
- REGULATORY_LOGGING is always True (hardcoded enterprise requirement)
- The class is importable and instantiable without errors
- Changes to settings are reflected (façade reads at class definition time)
"""

from __future__ import annotations

import unittest


class TestAletheiaConfigAttributes(unittest.TestCase):
    """AletheiaConfig class-level attributes must exist and have correct types."""

    def setUp(self) -> None:
        from bridge.config import AletheiaConfig
        self.config = AletheiaConfig

    def test_shadow_mode_attribute_exists(self) -> None:
        self.assertTrue(hasattr(self.config, "SHADOW_MODE"))

    def test_shadow_mode_is_bool(self) -> None:
        self.assertIsInstance(self.config.SHADOW_MODE, bool)

    def test_client_id_attribute_exists(self) -> None:
        self.assertTrue(hasattr(self.config, "CLIENT_ID"))

    def test_client_id_is_string(self) -> None:
        self.assertIsInstance(self.config.CLIENT_ID, str)

    def test_client_id_is_non_empty(self) -> None:
        self.assertGreater(len(self.config.CLIENT_ID), 0)

    def test_regulatory_logging_attribute_exists(self) -> None:
        self.assertTrue(hasattr(self.config, "REGULATORY_LOGGING"))

    def test_regulatory_logging_is_always_true(self) -> None:
        """This is a hardcoded enterprise compliance requirement."""
        self.assertTrue(self.config.REGULATORY_LOGGING)

    def test_threat_threshold_attribute_exists(self) -> None:
        self.assertTrue(hasattr(self.config, "THREAT_THRESHOLD"))

    def test_threat_threshold_is_float(self) -> None:
        self.assertIsInstance(self.config.THREAT_THRESHOLD, float)

    def test_threat_threshold_positive(self) -> None:
        self.assertGreater(self.config.THREAT_THRESHOLD, 0.0)

    def test_threat_threshold_in_reasonable_range(self) -> None:
        """Threat threshold should be a meaningful score (0 < x <= 10)."""
        self.assertLessEqual(self.config.THREAT_THRESHOLD, 10.0)


class TestAletheiaConfigSettingsAlignment(unittest.TestCase):
    """AletheiaConfig values must align with core.config.settings at import time."""

    def test_shadow_mode_matches_settings(self) -> None:
        from bridge.config import AletheiaConfig
        from core.config import settings
        self.assertEqual(AletheiaConfig.SHADOW_MODE, settings.shadow_mode)

    def test_client_id_matches_settings(self) -> None:
        from bridge.config import AletheiaConfig
        from core.config import settings
        self.assertEqual(AletheiaConfig.CLIENT_ID, settings.client_id)

    def test_threat_threshold_matches_policy_threshold(self) -> None:
        from bridge.config import AletheiaConfig
        from core.config import settings
        self.assertEqual(AletheiaConfig.THREAT_THRESHOLD, settings.policy_threshold)


class TestAletheiaConfigImportable(unittest.TestCase):
    """Importing the module and instantiating the class must not raise."""

    def test_module_importable(self) -> None:
        import bridge.config  # noqa: F401

    def test_class_importable(self) -> None:
        from bridge.config import AletheiaConfig
        self.assertIsNotNone(AletheiaConfig)

    def test_class_instantiable(self) -> None:
        from bridge.config import AletheiaConfig
        instance = AletheiaConfig()
        self.assertIsNotNone(instance)

    def test_class_attributes_accessible_on_instance(self) -> None:
        from bridge.config import AletheiaConfig
        instance = AletheiaConfig()
        self.assertIsInstance(instance.SHADOW_MODE, bool)
        self.assertIsInstance(instance.CLIENT_ID, str)
        self.assertIsInstance(instance.REGULATORY_LOGGING, bool)
        self.assertIsInstance(instance.THREAT_THRESHOLD, float)


if __name__ == "__main__":
    unittest.main()
