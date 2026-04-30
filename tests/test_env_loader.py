from __future__ import annotations

import os

from runtime.env_loader import load_env
from scripts.email_tool import _email_user


def test_env_agents_wins_over_env_template_defaults(tmp_path, monkeypatch):
    (tmp_path / ".env.agents").write_text(
        "HERMES_PO_PARSER=ollama-local\nEMAIL_USER=wizard@example.com\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "HERMES_PO_PARSER=auto\nEMAIL_PASSWORD=from-env\n",
        encoding="utf-8",
    )
    for key in ("HERMES_PO_PARSER", "EMAIL_USER", "EMAIL_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    load_env(tmp_path)

    assert os.getenv("HERMES_PO_PARSER") == "ollama-local"
    assert os.getenv("EMAIL_USER") == "wizard@example.com"
    assert os.getenv("EMAIL_PASSWORD") == "from-env"


def test_email_tool_accepts_canonical_email_user(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "orders@example.com")
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)

    assert _email_user() == "orders@example.com"


def test_email_tool_keeps_legacy_email_username(monkeypatch):
    monkeypatch.delenv("EMAIL_USER", raising=False)
    monkeypatch.setenv("EMAIL_USERNAME", "legacy@example.com")

    assert _email_user() == "legacy@example.com"
