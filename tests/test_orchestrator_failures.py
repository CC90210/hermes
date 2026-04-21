"""
tests/test_orchestrator_failures.py
------------------------------------
Tests for Orchestrator.handle_failures() retry/escalate logic and
run_cycle error handling.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from storage.db import OrderStatus, create_order, increment_retry_count, init_db, update_order_status


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

def _make_email_agent_stub() -> MagicMock:
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
# handle_failures: 2 failures → retry; 3rd → escalate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_failures_retries_then_escalates(
    mock_env: None, tmp_path: Path
) -> None:
    """After retry_count < _MAX_RETRIES the order is reset to PARSED;
    at retry_count >= _MAX_RETRIES escalate() is called exactly once."""
    db_path = tmp_path / "failures_test.db"
    await init_db(db_path)

    # Create an order that is already FAILED
    order_id = await create_order(
        db_path,
        po_number="PO-FAIL-001",
        customer_name="Test Co",
        customer_email="test@example.com",
        status=OrderStatus.FAILED,
    )

    email_stub = _make_email_agent_stub()
    a2000_stub = _make_a2000_stub()

    fake_config = SimpleNamespace(
        db_path=db_path,
        a2000_mode="mock",
        email_user="test@example.com",
        escalation_email="escalate@example.com",
        company_name="Test Co",
        log_dir=tmp_path,
    )

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=_make_po_parser_stub()),
        patch("manager.orchestrator.POSAgent", return_value=_make_pos_agent_stub()),
        patch("manager.orchestrator._build_a2000_client", return_value=a2000_stub),
        patch("manager.orchestrator.config", fake_config),
    ):
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()

        # --- First failure: retry_count=0 → should queue for retry ---
        await orch.handle_failures()
        from storage.db import get_order
        row = await get_order(db_path, order_id)
        assert row is not None
        assert row["status"] == OrderStatus.PARSED.value, "Should be reset to PARSED on first failure"
        assert row["retry_count"] == 1

        # Manually set back to FAILED to simulate next cycle
        await update_order_status(db_path, order_id, OrderStatus.FAILED)

        # --- Second failure: retry_count=1 → should queue for retry ---
        await orch.handle_failures()
        row = await get_order(db_path, order_id)
        assert row is not None
        assert row["status"] == OrderStatus.PARSED.value
        assert row["retry_count"] == 2

        # Manually set back to FAILED
        await update_order_status(db_path, order_id, OrderStatus.FAILED)

        # Bump retry_count to _MAX_RETRIES (3) so next call escalates
        await increment_retry_count(db_path, order_id)

        # --- Third failure: retry_count=3 → should escalate ---
        await orch.handle_failures()

        email_stub.send_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_failures_no_repeat_escalation(
    mock_env: None, tmp_path: Path
) -> None:
    """Calling handle_failures twice for the same max-retried order only escalates once."""
    db_path = tmp_path / "no_repeat_escalation.db"
    await init_db(db_path)

    order_id = await create_order(
        db_path,
        po_number="PO-ESCALATE-ONCE",
        customer_name="Test Co",
        customer_email="test@example.com",
        status=OrderStatus.FAILED,
    )
    # Push retry_count to _MAX_RETRIES
    for _ in range(3):
        await increment_retry_count(db_path, order_id)

    email_stub = _make_email_agent_stub()

    fake_config = SimpleNamespace(
        db_path=db_path,
        a2000_mode="mock",
        email_user="test@example.com",
        escalation_email="escalate@example.com",
        company_name="Test Co",
        log_dir=tmp_path,
    )

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=_make_po_parser_stub()),
        patch("manager.orchestrator.POSAgent", return_value=_make_pos_agent_stub()),
        patch("manager.orchestrator._build_a2000_client", return_value=_make_a2000_stub()),
        patch("manager.orchestrator.config", fake_config),
    ):
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()

        # First call → escalates
        await orch.handle_failures()
        assert email_stub.send_alert.await_count == 1

        # Second call → already escalated, should NOT escalate again
        await orch.handle_failures()
        assert email_stub.send_alert.await_count == 1, "Should not escalate the same order twice"


# ---------------------------------------------------------------------------
# run_cycle: poll_inbox raising an exception
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_cycle_email_poll_exception_returns_zeros(
    mock_env: None, tmp_path: Path
) -> None:
    """run_cycle returns {processed:0, failed:0} when poll_inbox raises."""
    db_path = tmp_path / "poll_error.db"
    await init_db(db_path)

    email_stub = _make_email_agent_stub()
    email_stub.poll_inbox = AsyncMock(side_effect=ConnectionError("IMAP timeout"))

    fake_config = SimpleNamespace(
        db_path=db_path,
        a2000_mode="mock",
        email_user="test@example.com",
        escalation_email="escalate@example.com",
        company_name="Test Co",
        log_dir=tmp_path,
    )

    with (
        patch("manager.orchestrator.EmailAgent", return_value=email_stub),
        patch("manager.orchestrator.POParser", return_value=_make_po_parser_stub()),
        patch("manager.orchestrator.POSAgent", return_value=_make_pos_agent_stub()),
        patch("manager.orchestrator._build_a2000_client", return_value=_make_a2000_stub()),
        patch("manager.orchestrator.config", fake_config),
    ):
        from manager.orchestrator import Orchestrator

        orch = Orchestrator()
        summary = await orch.run_cycle()

    assert summary["processed"] == 0
    assert summary["failed"] == 0
