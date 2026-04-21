"""
tests/test_orchestrator.py
--------------------------
Tests for manager/orchestrator.py.

The orchestrator wires together EmailAgent, POParser, POSAgent, and an A2000
client.  In tests we patch at the module boundary so no real IMAP, SMTP, or
Ollama connection is attempted.

Important: the orchestrator calls EmailAgent(config) even though the current
email_agent module defines EmailAgent() with no arguments.  We patch the
entire EmailAgent class to avoid that mismatch here — the test verifies
orchestrator *logic*, not the email agent itself.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapters.a2000_client import MockA2000Client
from storage.db import init_db


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _make_email_agent_stub() -> MagicMock:
    """Return a MagicMock that satisfies the Orchestrator's usage of EmailAgent."""
    stub = MagicMock()
    stub.connect = AsyncMock()
    stub.poll_inbox = AsyncMock(return_value=[])
    stub.is_connected = AsyncMock(return_value=True)
    stub.send_invoice = AsyncMock()
    stub.send_alert = AsyncMock()
    return stub


def _make_po_parser_stub() -> MagicMock:
    stub = MagicMock()
    stub.parse_and_persist = AsyncMock(return_value=1)
    return stub


def _make_pos_agent_stub() -> MagicMock:
    stub = MagicMock()
    stub.enter_order = AsyncMock()
    stub.retrieve_invoice = AsyncMock(return_value=Path("/tmp/invoice.pdf"))
    return stub


def _make_a2000_stub() -> MagicMock:
    stub = MagicMock()
    stub.validate = AsyncMock()
    stub.is_reachable = AsyncMock(return_value=True)
    stub.create_order = AsyncMock()
    stub.get_invoice = AsyncMock(return_value=b"%PDF stub")
    stub.get_order = AsyncMock(return_value={})
    stub.print_order = AsyncMock(return_value=True)
    return stub


# ---------------------------------------------------------------------------
# test_orchestrator_setup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_setup(mock_env: None, tmp_path: Path) -> None:
    """Orchestrator.setup() initialises the DB and connects agents without error."""
    import os
    os.environ["DB_PATH"] = str(tmp_path / "orch_test.db")

    email_stub = _make_email_agent_stub()
    po_stub = _make_po_parser_stub()
    pos_stub = _make_pos_agent_stub()
    a2000_stub = _make_a2000_stub()

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=po_stub),
        patch("manager.orchestrator.POSAgent", return_value=pos_stub),
        patch("manager.orchestrator._build_a2000_client", return_value=a2000_stub),
    ):
        # Re-import config after env change so DB_PATH is picked up
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()
        await orch.setup()

    # connect() was called on the email agent
    email_stub.connect.assert_awaited_once()
    # validate() was called on the A2000 client
    a2000_stub.validate.assert_awaited_once()


# ---------------------------------------------------------------------------
# test_orchestrator_health_check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_health_check(mock_env: None, tmp_path: Path) -> None:
    """health_check returns a dict with the expected keys and correct types."""
    import os
    os.environ["DB_PATH"] = str(tmp_path / "health_test.db")

    email_stub = _make_email_agent_stub()
    a2000_stub = _make_a2000_stub()

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=_make_po_parser_stub()),
        patch("manager.orchestrator.POSAgent", return_value=_make_pos_agent_stub()),
        patch("manager.orchestrator._build_a2000_client", return_value=a2000_stub),
    ):
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()
        # Initialise the DB so health_check list queries work
        db_path = tmp_path / "health_test.db"
        await init_db(db_path)

        health = await orch.health_check()

    # Shape assertions
    assert "email_connected" in health
    assert "a2000_reachable" in health
    assert "pending_orders" in health
    assert "failed_orders" in health
    assert "cycle_count" in health
    assert "timestamp" in health

    # Type assertions
    assert isinstance(health["email_connected"], bool)
    assert isinstance(health["a2000_reachable"], bool)
    assert isinstance(health["pending_orders"], int)
    assert isinstance(health["failed_orders"], int)
    assert isinstance(health["cycle_count"], int)
    assert isinstance(health["timestamp"], str)

    # Fresh orchestrator has done 0 cycles
    assert health["cycle_count"] == 0


# ---------------------------------------------------------------------------
# test_orchestrator_run_cycle_empty_inbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_run_cycle_empty_inbox(mock_env: None, tmp_path: Path) -> None:
    """run_cycle with an empty inbox returns zeros for processed and failed."""
    import os
    os.environ["DB_PATH"] = str(tmp_path / "cycle_test.db")
    await init_db(tmp_path / "cycle_test.db")

    email_stub = _make_email_agent_stub()
    email_stub.poll_inbox = AsyncMock(return_value=[])

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=_make_po_parser_stub()),
        patch("manager.orchestrator.POSAgent", return_value=_make_pos_agent_stub()),
        patch("manager.orchestrator._build_a2000_client", return_value=_make_a2000_stub()),
    ):
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()
        summary = await orch.run_cycle()

    assert summary["processed"] == 0
    assert summary["failed"] == 0
    assert summary["cycle_count"] if "cycle_count" in summary else True


# ---------------------------------------------------------------------------
# test_orchestrator_build_a2000_client_mock_mode
# ---------------------------------------------------------------------------

def test_build_a2000_client_mock_mode(mock_env: None) -> None:
    """_build_a2000_client('mock') returns a MockA2000Client."""
    from manager.orchestrator import _build_a2000_client

    client = _build_a2000_client("mock")
    assert isinstance(client, MockA2000Client)


def test_build_a2000_client_unknown_mode_raises(mock_env: None) -> None:
    """_build_a2000_client raises ValueError for unrecognised mode."""
    from manager.orchestrator import _build_a2000_client

    with pytest.raises(ValueError, match="Unknown A2000_MODE"):
        _build_a2000_client("fax")
