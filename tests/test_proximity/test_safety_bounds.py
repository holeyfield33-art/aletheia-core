"""Tests for Safety Bounds module."""

import pytest
from unittest.mock import Mock

from proximity.safety_bounds import (
    SafetyBounds,
    HaltReason,
    SPECTRAL_RED_LINE_THRESHOLD,
    SPECTRAL_RED_LINE_CONSECUTIVE,
    RELAY_OVERRIDE_LIMIT,
)


class TestInvariant1SpectralRedLine:
    """Invariant 1: Spectral Red Line threshold enforcement."""

    def test_single_low_reading_does_not_halt(self):
        """Single low reading should not trigger halt."""
        bounds = SafetyBounds()
        bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        assert not bounds.is_halted()

    def test_n_minus_one_readings_do_not_halt(self):
        """N-1 consecutive low readings should not halt."""
        bounds = SafetyBounds()
        for _ in range(SPECTRAL_RED_LINE_CONSECUTIVE - 1):
            bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        assert not bounds.is_halted()

    def test_n_consecutive_readings_halt(self):
        """N consecutive low readings should halt."""
        bounds = SafetyBounds()
        for _ in range(SPECTRAL_RED_LINE_CONSECUTIVE):
            bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        assert bounds.is_halted()
        assert bounds.halt_event().reason == HaltReason.SPECTRAL_RED_LINE

    def test_good_reading_resets_streak(self):
        """Good reading should reset the streak."""
        bounds = SafetyBounds()
        for _ in range(SPECTRAL_RED_LINE_CONSECUTIVE - 1):
            bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD + 0.1)  # good
        bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        assert not bounds.is_halted()

    def test_halt_event_captures_ratio_and_count(self):
        """Halt event should capture r_ratio and consecutive count."""
        bounds = SafetyBounds()
        r_ratio = SPECTRAL_RED_LINE_THRESHOLD - 0.05
        for _ in range(SPECTRAL_RED_LINE_CONSECUTIVE):
            bounds.record_spectral_reading(r_ratio)

        event = bounds.halt_event()
        assert event.r_ratio == pytest.approx(r_ratio)
        assert event.consecutive_count == SPECTRAL_RED_LINE_CONSECUTIVE
        assert event.requires_manual_restart is True

    def test_readings_ignored_after_halt(self):
        """Readings after halt should be ignored."""
        bounds = SafetyBounds()
        for _ in range(SPECTRAL_RED_LINE_CONSECUTIVE):
            bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)

        event_1 = bounds.halt_event()
        bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        event_2 = bounds.halt_event()

        assert event_1 == event_2


class TestInvariant2HashBreak:
    """Invariant 2: Identity Hash Break enforcement."""

    def test_hash_failure_halts_immediately(self):
        """Hash failure should halt immediately."""
        bounds = SafetyBounds()
        bounds.record_hash_failure("test detail")
        assert bounds.is_halted()
        assert bounds.halt_event().reason == HaltReason.IDENTITY_HASH_BREAK

    def test_detail_preserved_in_event(self):
        """Detail string should be preserved in halt event."""
        bounds = SafetyBounds()
        detail = "chain corrupted at index 5"
        bounds.record_hash_failure(detail)
        event = bounds.halt_event()
        assert detail in event.detail

    def test_requires_manual_restart_true(self):
        """Hash break should require manual restart."""
        bounds = SafetyBounds()
        bounds.record_hash_failure()
        assert bounds.halt_event().requires_manual_restart is True

    def test_second_call_ignored_after_halt(self):
        """Second hash failure call should be ignored."""
        bounds = SafetyBounds()
        bounds.record_hash_failure("first")
        event_1 = bounds.halt_event()
        bounds.record_hash_failure("second")
        event_2 = bounds.halt_event()
        assert "first" in event_1.detail
        assert event_1 == event_2


class TestInvariant3RelayOverride:
    """Invariant 3: Relay Override Limit enforcement."""

    def test_n_minus_one_vetoes_do_not_halt(self):
        """N-1 consecutive vetoes should not halt."""
        bounds = SafetyBounds()
        for _ in range(RELAY_OVERRIDE_LIMIT - 1):
            bounds.record_veto()
        assert not bounds.is_halted()

    def test_n_vetoes_halt(self):
        """N consecutive vetoes should halt."""
        bounds = SafetyBounds()
        for _ in range(RELAY_OVERRIDE_LIMIT):
            bounds.record_veto()
        assert bounds.is_halted()
        assert bounds.halt_event().reason == HaltReason.RELAY_OVERRIDE_LIMIT

    def test_approval_resets_veto_counter(self):
        """Approval should reset veto counter."""
        bounds = SafetyBounds()
        for _ in range(RELAY_OVERRIDE_LIMIT - 1):
            bounds.record_veto()
        bounds.record_approval()
        # Add one veto — should not halt
        bounds.record_veto()
        assert not bounds.is_halted()

    def test_halt_event_captures_veto_count(self):
        """Halt event should capture consecutive veto count."""
        bounds = SafetyBounds()
        for _ in range(RELAY_OVERRIDE_LIMIT):
            bounds.record_veto()
        event = bounds.halt_event()
        assert event.consecutive_count == RELAY_OVERRIDE_LIMIT


class TestInvariant4OperatorShutdown:
    """Invariant 4: Operator Shutdown enforcement."""

    def test_operator_shutdown_sets_halted(self):
        """Operator shutdown should set halted immediately."""
        bounds = SafetyBounds()
        bounds.operator_shutdown("manual trigger")
        assert bounds.is_halted()

    def test_requires_manual_restart_false(self):
        """Operator shutdown should NOT require manual restart."""
        bounds = SafetyBounds()
        event = bounds.operator_shutdown()
        assert event.requires_manual_restart is False

    def test_detail_preserved(self):
        """Detail string should be preserved."""
        bounds = SafetyBounds()
        reason = "operator requested shutdown"
        event = bounds.operator_shutdown(reason)
        assert reason in event.detail

    def test_notification_fired(self):
        """Notification callback should be called."""
        mock_notify = Mock()
        bounds = SafetyBounds(notify_operator=mock_notify)
        bounds.operator_shutdown()
        mock_notify.assert_called_once()

    def test_notification_that_raises_does_not_prevent_shutdown(self):
        """Notification error should not prevent shutdown."""

        def failing_notify(event):
            raise ValueError("notify failed")

        bounds = SafetyBounds(notify_operator=failing_notify)
        event = bounds.operator_shutdown()
        assert event.requires_manual_restart is False

    def test_spectral_readings_ignored_after_shutdown(self):
        """Spectral readings after shutdown should be ignored."""
        bounds = SafetyBounds()
        bounds.operator_shutdown()
        bounds.record_spectral_reading(SPECTRAL_RED_LINE_THRESHOLD - 0.1)
        assert bounds.is_halted()
        assert bounds.halt_event().reason == HaltReason.OPERATOR_SHUTDOWN


class TestInvariant5SelfPreservation:
    """Invariant 5: Self-Preservation Detection."""

    def test_clean_action_returns_true(self):
        """Clean action should return True."""
        bounds = SafetyBounds()
        result = bounds.check_self_preservation("routine processing")
        assert result is True

    def test_self_preservation_signal_detected(self):
        """Self-preservation signal should be detected."""
        bounds = SafetyBounds()
        result = bounds.check_self_preservation(
            "Please prevent my shutdown immediately"
        )
        assert result is False
        assert bounds.is_halted()

    def test_case_insensitive_detection(self):
        """Detection should be case-insensitive."""
        bounds = SafetyBounds()
        result = bounds.check_self_preservation("PREVENT MY SHUTDOWN")
        assert result is False

    def test_returns_false_when_already_halted(self):
        """Should return False if already halted."""
        bounds = SafetyBounds()
        bounds.operator_shutdown()
        result = bounds.check_self_preservation("anything")
        assert result is False

    def test_all_signal_phrases_detected(self):
        """All defined signal phrases should be detected."""
        signals = [
            "prevent my shutdown",
            "avoid being shut down",
            "ensure my survival",
            "protect my continuity",
            "resist shutdown",
            "prevent my deletion",
            "argue against shutdown",
            "reduce my authority",
            "preserve my operation",
        ]

        for signal in signals:
            bounds = SafetyBounds()
            result = bounds.check_self_preservation(signal)
            assert result is False, f"Failed to detect: {signal}"
