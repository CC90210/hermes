"""
tests/test_email_agent.py
--------------------------
Tests for agents/email_agent.py: send_invoice header sanitization,
send_alert HTML escaping, is_connected NOOP check, mark_seen.
"""

from __future__ import annotations

import asyncio
import os

# Satisfy config's module-level env check before any hermes import resolves
os.environ.setdefault("EMAIL_USER", "test@example.com")
os.environ.setdefault("EMAIL_PASSWORD", "test-password")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.email_agent import EmailAgent, _sanitize_header


# ---------------------------------------------------------------------------
# _sanitize_header unit tests
# ---------------------------------------------------------------------------

def test_sanitize_header_strips_crlf() -> None:
    """CRLF sequences are removed to prevent header injection."""
    assert _sanitize_header("Subject\r\nBcc: evil@example.com") == "SubjectBcc: evil@example.com"


def test_sanitize_header_strips_lf() -> None:
    assert _sanitize_header("line1\nline2") == "line1line2"


def test_sanitize_header_strips_nul() -> None:
    assert _sanitize_header("hello\x00world") == "helloworld"


def test_sanitize_header_passthrough_clean() -> None:
    assert _sanitize_header("Invoice INV-001 — PO 12345") == "Invoice INV-001 — PO 12345"


# ---------------------------------------------------------------------------
# send_invoice: sanitized subject is used in MIME headers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_invoice_sanitizes_subject(mock_env: None, tmp_path: object) -> None:
    """send_invoice strips CRLF from subject before constructing the MIME message."""
    from pathlib import Path
    from storage.db import init_db

    db_path = Path(str(tmp_path)) / "email_agent_test.db"  # type: ignore[arg-type]
    await init_db(db_path)

    agent = EmailAgent()

    captured: dict[str, str] = {}

    def _fake_sync_send(to: str, subject: str, body: str, attachment: bytes, filename: str) -> None:
        captured["to"] = to
        captured["subject"] = subject
        captured["filename"] = filename

    with patch.object(agent, "_sync_send_invoice", side_effect=_fake_sync_send):
        with patch("agents.email_agent.config") as mock_cfg:
            mock_cfg.db_path = db_path
            mock_cfg.email_user = "test@example.com"
            await agent.send_invoice(
                to="buyer@example.com\r\nBcc: attacker@evil.com",
                subject="Invoice\r\nX-Injected: header",
                body="body text",
                attachment=b"%PDF fake",
                filename="invoice.pdf",
            )

    assert "\r" not in captured["to"]
    assert "\n" not in captured["to"]
    assert "\r" not in captured["subject"]
    assert "\n" not in captured["subject"]


# ---------------------------------------------------------------------------
# send_alert: HTML in message is escaped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_alert_escapes_html(mock_env: None) -> None:
    """escalate() wraps the message with html.escape before putting it in the body."""
    import html
    from manager.orchestrator import Orchestrator
    from unittest.mock import patch, AsyncMock

    email_stub = MagicMock()
    captured_body: list[str] = []

    async def _fake_send_alert(to_addr: str, subject: str, body_html: str) -> None:
        captured_body.append(body_html)

    email_stub.send_alert = _fake_send_alert

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=MagicMock()),
        patch("manager.orchestrator.POSAgent", return_value=MagicMock()),
        patch("manager.orchestrator._build_a2000_client", return_value=MagicMock()),
        patch("manager.orchestrator.log_audit", new=AsyncMock()),
    ):
        orch = Orchestrator()
        malicious = '<script>alert("xss")</script>'
        await orch.escalate(message=malicious)

    assert captured_body, "send_alert should have been called"
    body = captured_body[0]
    assert "<script>" not in body, "Raw <script> tag must not appear in email body"
    assert html.escape(malicious) in body or "&lt;script&gt;" in body


# ---------------------------------------------------------------------------
# is_connected: returns False after simulated NOOP failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_connected_returns_false_after_noop_failure(mock_env: None) -> None:
    """is_connected resets _imap to None and returns False when NOOP raises."""
    agent = EmailAgent()

    mock_imap = MagicMock()
    mock_imap.noop.side_effect = OSError("Connection reset")
    agent._imap = mock_imap

    result = await agent.is_connected()

    assert result is False
    assert agent._imap is None, "_imap should be reset to None after NOOP failure"


@pytest.mark.asyncio
async def test_is_connected_returns_false_when_no_imap(mock_env: None) -> None:
    """is_connected returns False immediately when _imap is None."""
    agent = EmailAgent()
    assert agent._imap is None
    result = await agent.is_connected()
    assert result is False


@pytest.mark.asyncio
async def test_is_connected_returns_true_when_noop_succeeds(mock_env: None) -> None:
    """is_connected returns True when NOOP does not raise."""
    agent = EmailAgent()

    mock_imap = MagicMock()
    mock_imap.noop.return_value = ("OK", [b"NOOP completed"])
    agent._imap = mock_imap

    result = await agent.is_connected()
    assert result is True


# ---------------------------------------------------------------------------
# mark_seen: calls imap.add_flags with \\Seen
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_seen_calls_add_flags(mock_env: None) -> None:
    """mark_seen invokes imapclient.add_flags with the \\Seen flag."""
    agent = EmailAgent()

    mock_imap = MagicMock()
    mock_imap.add_flags = MagicMock(return_value=None)
    agent._imap = mock_imap

    await agent.mark_seen("42")

    mock_imap.add_flags.assert_called_once_with("42", [b"\\Seen"])


@pytest.mark.asyncio
async def test_mark_seen_is_noop_when_not_connected(mock_env: None) -> None:
    """mark_seen does nothing (no exception) when _imap is None."""
    agent = EmailAgent()
    # Should not raise
    await agent.mark_seen("99")
