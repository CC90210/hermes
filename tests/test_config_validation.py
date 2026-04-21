"""
tests/test_config_validation.py
--------------------------------
Tests for manager/config.py mode-specific required variable validation.
"""

from __future__ import annotations

import sys

import pytest


def _reload_config_with_env(monkeypatch: pytest.MonkeyPatch, extra: dict[str, str]) -> None:
    """Set env vars and force-reload config module so _validated_a2000_mode runs fresh."""
    base = {
        "EMAIL_USER": "test@example.com",
        "EMAIL_PASSWORD": "test-password",
        "ESCALATION_EMAIL": "escalation@example.com",
    }
    base.update(extra)
    for key, value in base.items():
        monkeypatch.setenv(key, value)
    # Clear any cached value of A2000_MODE-related vars not in extra
    for key in ("A2000_API_URL", "A2000_API_KEY", "EDI_OUTPUT_DIR", "EDI_SENDER_ID", "EDI_RECEIVER_ID"):
        if key not in extra:
            monkeypatch.delenv(key, raising=False)
    # Remove cached module so it re-executes at import time
    for mod in list(sys.modules.keys()):
        if "manager.config" in mod or mod == "manager.config":
            del sys.modules[mod]


# ---------------------------------------------------------------------------
# A2000_MODE=api without required vars
# ---------------------------------------------------------------------------

def test_api_mode_without_api_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=api without A2000_API_URL raises EnvironmentError."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "api",
        "A2000_API_KEY": "some-key",
        # A2000_API_URL intentionally absent
    })
    with pytest.raises(EnvironmentError, match="A2000_API_URL"):
        import manager.config  # noqa: F401


def test_api_mode_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=api without A2000_API_KEY raises EnvironmentError."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "api",
        "A2000_API_URL": "http://a2000.example.com",
        # A2000_API_KEY intentionally absent
    })
    with pytest.raises(EnvironmentError, match="A2000_API_KEY"):
        import manager.config  # noqa: F401


def test_api_mode_with_all_required_vars_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=api with both required vars set loads without error."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "api",
        "A2000_API_URL": "http://a2000.example.com",
        "A2000_API_KEY": "some-key",
    })
    import manager.config  # should not raise
    assert manager.config.config.a2000_mode == "api"


# ---------------------------------------------------------------------------
# A2000_MODE=edi without required vars
# ---------------------------------------------------------------------------

def test_edi_mode_without_output_dir_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=edi without EDI_OUTPUT_DIR raises EnvironmentError."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "edi",
        "EDI_SENDER_ID": "SENDER",
        "EDI_RECEIVER_ID": "RECEIVER",
        # EDI_OUTPUT_DIR intentionally absent
    })
    with pytest.raises(EnvironmentError, match="EDI_OUTPUT_DIR"):
        import manager.config  # noqa: F401


def test_edi_mode_without_sender_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=edi without EDI_SENDER_ID raises EnvironmentError."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "edi",
        "EDI_OUTPUT_DIR": "/tmp/edi",
        "EDI_RECEIVER_ID": "RECEIVER",
        # EDI_SENDER_ID intentionally absent
    })
    with pytest.raises(EnvironmentError, match="EDI_SENDER_ID"):
        import manager.config  # noqa: F401


def test_edi_mode_without_receiver_id_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=edi without EDI_RECEIVER_ID raises EnvironmentError."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "edi",
        "EDI_OUTPUT_DIR": "/tmp/edi",
        "EDI_SENDER_ID": "SENDER",
        # EDI_RECEIVER_ID intentionally absent
    })
    with pytest.raises(EnvironmentError, match="EDI_RECEIVER_ID"):
        import manager.config  # noqa: F401


def test_edi_mode_with_all_required_vars_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=edi with all three required vars set loads without error."""
    _reload_config_with_env(monkeypatch, {
        "A2000_MODE": "edi",
        "EDI_OUTPUT_DIR": "/tmp/edi_out",
        "EDI_SENDER_ID": "SENDER",
        "EDI_RECEIVER_ID": "RECEIVER",
    })
    import manager.config
    assert manager.config.config.a2000_mode == "edi"


# ---------------------------------------------------------------------------
# A2000_MODE=mock (default) — no extra vars needed
# ---------------------------------------------------------------------------

def test_mock_mode_requires_no_extra_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """A2000_MODE=mock loads cleanly with only the base required vars."""
    _reload_config_with_env(monkeypatch, {"A2000_MODE": "mock"})
    import manager.config
    assert manager.config.config.a2000_mode == "mock"


# ---------------------------------------------------------------------------
# FIX 5 — ESCALATION_EMAIL is required
# ---------------------------------------------------------------------------

def test_missing_escalation_email_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config raises EnvironmentError when ESCALATION_EMAIL is not set."""
    for mod in list(sys.modules.keys()):
        if "manager.config" in mod or mod == "manager.config":
            del sys.modules[mod]
    monkeypatch.setenv("EMAIL_USER", "test@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "test-password")
    monkeypatch.setenv("A2000_MODE", "mock")
    monkeypatch.delenv("ESCALATION_EMAIL", raising=False)

    import manager.config
    assert manager.config.config.escalation_email == ""
    with pytest.raises(EnvironmentError, match="ESCALATION_EMAIL"):
        manager.config.require_escalation_email()


def test_present_escalation_email_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config loads without error when ESCALATION_EMAIL is set."""
    _reload_config_with_env(monkeypatch, {"A2000_MODE": "mock", "ESCALATION_EMAIL": "alerts@example.com"})
    import manager.config
    assert manager.config.config.escalation_email == "alerts@example.com"
