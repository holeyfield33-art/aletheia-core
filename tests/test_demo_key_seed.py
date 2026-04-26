from __future__ import annotations

from unittest.mock import Mock


def test_seed_demo_key_prefers_demo_env(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.return_value = None
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.setenv("ALETHEIA_DEMO_API_KEY", "sk_trial_demo_123")
    monkeypatch.setenv("ALETHEIA_API_KEY", "sk_trial_fallback_456")

    wrapper._seed_demo_key()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_demo_123")
    key_store.import_raw_key.assert_called_once()
    assert key_store.import_raw_key.call_args.kwargs["raw_key"] == "sk_trial_demo_123"


def test_seed_demo_key_uses_api_key_fallback(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.return_value = None
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.delenv("ALETHEIA_DEMO_API_KEY", raising=False)
    monkeypatch.setenv("ALETHEIA_API_KEY", "sk_trial_fallback_456")

    wrapper._seed_demo_key()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_fallback_456")
    key_store.import_raw_key.assert_called_once()
    assert (
        key_store.import_raw_key.call_args.kwargs["raw_key"] == "sk_trial_fallback_456"
    )


def test_seed_demo_key_no_env_noop(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.delenv("ALETHEIA_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_API_KEY", raising=False)

    wrapper._seed_demo_key()

    key_store.lookup_by_hash.assert_not_called()
    key_store.import_raw_key.assert_not_called()


def test_seed_demo_key_skips_import_when_record_exists(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.return_value = object()
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.setenv("ALETHEIA_DEMO_API_KEY", "sk_trial_demo_123")

    wrapper._seed_demo_key()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_demo_123")
    key_store.import_raw_key.assert_not_called()


def test_seed_demo_key_lookup_failure_is_fail_safe(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.side_effect = RuntimeError("db down")
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.setenv("ALETHEIA_DEMO_API_KEY", "sk_trial_demo_123")

    wrapper._seed_demo_key()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_demo_123")
    key_store.import_raw_key.assert_not_called()


def test_demo_key_health_signal_not_configured(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    monkeypatch.delenv("ALETHEIA_DEMO_API_KEY", raising=False)
    monkeypatch.delenv("ALETHEIA_API_KEY", raising=False)

    health = wrapper._demo_key_health_signal()

    assert health["configured"] is False
    assert health["registered"] is False
    assert health["status"] == "not_configured"


def test_demo_key_health_signal_registered(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.return_value = object()
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.setenv("ALETHEIA_DEMO_API_KEY", "sk_trial_demo_123")

    health = wrapper._demo_key_health_signal()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_demo_123")
    assert health["configured"] is True
    assert health["registered"] is True
    assert health["status"] == "registered"


def test_demo_key_health_signal_missing(monkeypatch) -> None:
    import bridge.fastapi_wrapper as wrapper

    key_store = Mock()
    key_store.lookup_by_hash.return_value = None
    monkeypatch.setattr(wrapper, "key_store", key_store)
    monkeypatch.delenv("ALETHEIA_DEMO_API_KEY", raising=False)
    monkeypatch.setenv("ALETHEIA_API_KEY", "sk_trial_fallback_456")

    health = wrapper._demo_key_health_signal()

    key_store.lookup_by_hash.assert_called_once_with("sk_trial_fallback_456")
    assert health["configured"] is True
    assert health["registered"] is False
    assert health["status"] == "missing"
    assert health["source"] == "ALETHEIA_API_KEY"
