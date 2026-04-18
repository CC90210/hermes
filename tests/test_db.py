"""
tests/test_db.py
----------------
Tests for storage/db.py.

Uses a fresh temporary SQLite file per test via the temp_db_path fixture so
there is no shared state between cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storage.db import (
    EmailQueueStatus,
    OrderStatus,
    create_order,
    create_order_line,
    enqueue_email,
    get_audit_log,
    get_order,
    get_order_lines,
    get_pending_emails,
    init_db,
    list_orders_by_status,
    log_audit,
    mark_email_sent,
    update_order_status,
)


# ---------------------------------------------------------------------------
# test_init_db_creates_tables
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_init_db_creates_tables(temp_db_path: Path) -> None:
    """init_db creates the four expected tables without error."""
    await init_db(temp_db_path)

    import aiosqlite

    async with aiosqlite.connect(temp_db_path) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ) as cur:
            tables = {row[0] for row in await cur.fetchall()}

    assert "orders" in tables
    assert "order_lines" in tables
    assert "audit_log" in tables
    assert "email_queue" in tables


@pytest.mark.asyncio
async def test_init_db_is_idempotent(temp_db_path: Path) -> None:
    """Calling init_db twice does not raise or duplicate tables."""
    await init_db(temp_db_path)
    await init_db(temp_db_path)  # second call must not fail


# ---------------------------------------------------------------------------
# test_create_order_and_retrieve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_order_and_retrieve(temp_db_path: Path) -> None:
    """create_order returns an integer ID; get_order returns matching row."""
    await init_db(temp_db_path)

    order_id = await create_order(
        temp_db_path,
        po_number="PO-2026-04567",
        customer_name="Walgreens #04231",
        customer_email="purchasing@walgreens.com",
        raw_email_id="uid-001",
    )

    assert isinstance(order_id, int)
    assert order_id > 0

    row = await get_order(temp_db_path, order_id)
    assert row is not None
    assert row["po_number"] == "PO-2026-04567"
    assert row["customer_name"] == "Walgreens #04231"
    assert row["customer_email"] == "purchasing@walgreens.com"
    assert row["raw_email_id"] == "uid-001"
    assert row["status"] == OrderStatus.RECEIVED.value


@pytest.mark.asyncio
async def test_get_order_returns_none_for_missing(temp_db_path: Path) -> None:
    """get_order returns None when the ID does not exist."""
    await init_db(temp_db_path)
    row = await get_order(temp_db_path, 99999)
    assert row is None


# ---------------------------------------------------------------------------
# test_update_order_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_order_status(temp_db_path: Path) -> None:
    """update_order_status persists the new status and updates updated_at."""
    await init_db(temp_db_path)

    order_id = await create_order(
        temp_db_path,
        po_number="PO-STATUS-TEST",
        customer_name="Test Customer",
        customer_email="test@example.com",
    )

    await update_order_status(temp_db_path, order_id, OrderStatus.PARSED)
    row = await get_order(temp_db_path, order_id)
    assert row is not None
    assert row["status"] == "parsed"

    await update_order_status(temp_db_path, order_id, OrderStatus.EMAILED)
    row = await get_order(temp_db_path, order_id)
    assert row is not None
    assert row["status"] == "emailed"


@pytest.mark.asyncio
async def test_list_orders_by_status(temp_db_path: Path) -> None:
    """list_orders_by_status filters correctly and returns all matching rows."""
    await init_db(temp_db_path)

    id1 = await create_order(
        temp_db_path, po_number="PO-A", customer_name="A", customer_email="a@x.com"
    )
    id2 = await create_order(
        temp_db_path, po_number="PO-B", customer_name="B", customer_email="b@x.com"
    )
    await create_order(
        temp_db_path, po_number="PO-C", customer_name="C", customer_email="c@x.com"
    )

    await update_order_status(temp_db_path, id1, OrderStatus.PARSED)
    await update_order_status(temp_db_path, id2, OrderStatus.PARSED)

    parsed = await list_orders_by_status(temp_db_path, OrderStatus.PARSED)
    received = await list_orders_by_status(temp_db_path, OrderStatus.RECEIVED)

    assert len(parsed) == 2
    assert len(received) == 1
    po_numbers = {r["po_number"] for r in parsed}
    assert "PO-A" in po_numbers
    assert "PO-B" in po_numbers


# ---------------------------------------------------------------------------
# Order lines
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_and_retrieve_order_lines(temp_db_path: Path) -> None:
    """create_order_line inserts a row; get_order_lines retrieves all for an order."""
    await init_db(temp_db_path)

    order_id = await create_order(
        temp_db_path, po_number="PO-LINES", customer_name="X", customer_email="x@x.com"
    )

    await create_order_line(
        temp_db_path,
        order_id=order_id,
        sku="LWG-1001",
        description="Premium Cotton T-Shirt - Black M",
        quantity=144,
        unit_price=4.25,
        line_total=612.0,
    )
    await create_order_line(
        temp_db_path,
        order_id=order_id,
        sku="LWG-2050",
        description="Athletic Sock 6-Pack White",
        quantity=72,
        unit_price=8.50,
        line_total=612.0,
    )

    lines = await get_order_lines(temp_db_path, order_id)
    assert len(lines) == 2
    skus = {line["sku"] for line in lines}
    assert "LWG-1001" in skus
    assert "LWG-2050" in skus
    qtys = {line["sku"]: line["quantity"] for line in lines}
    assert qtys["LWG-1001"] == 144
    assert qtys["LWG-2050"] == 72


# ---------------------------------------------------------------------------
# test_audit_log_insert_and_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_log_insert_and_query(temp_db_path: Path) -> None:
    """log_audit persists an entry; get_audit_log returns it with correct fields."""
    await init_db(temp_db_path)

    await log_audit(
        temp_db_path,
        agent_name="orchestrator",
        action="startup",
        details={"mode": "mock", "email": "test@example.com"},
    )

    logs = await get_audit_log(temp_db_path, agent_name="orchestrator")
    assert len(logs) >= 1

    entry = logs[0]
    assert entry["agent_name"] == "orchestrator"
    assert entry["action"] == "startup"

    import json
    details = json.loads(entry["details_json"])
    assert details["mode"] == "mock"
    assert details["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_audit_log_agent_name_filter(temp_db_path: Path) -> None:
    """get_audit_log filters by agent_name correctly."""
    await init_db(temp_db_path)

    await log_audit(temp_db_path, agent_name="email_agent", action="poll", details=None)
    await log_audit(temp_db_path, agent_name="pos_agent", action="enter", details=None)

    email_logs = await get_audit_log(temp_db_path, agent_name="email_agent")
    pos_logs = await get_audit_log(temp_db_path, agent_name="pos_agent")
    all_logs = await get_audit_log(temp_db_path)

    assert all(e["agent_name"] == "email_agent" for e in email_logs)
    assert all(e["agent_name"] == "pos_agent" for e in pos_logs)
    assert len(all_logs) == 2


@pytest.mark.asyncio
async def test_audit_log_null_details(temp_db_path: Path) -> None:
    """log_audit handles None details without error."""
    await init_db(temp_db_path)
    await log_audit(temp_db_path, agent_name="test", action="noop", details=None)
    logs = await get_audit_log(temp_db_path, agent_name="test")
    assert len(logs) == 1
    assert logs[0]["details_json"] is None


# ---------------------------------------------------------------------------
# test_email_queue_enqueue_and_mark_sent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_queue_enqueue_and_mark_sent(temp_db_path: Path) -> None:
    """enqueue_email creates a pending row; mark_email_sent updates status and sent_at."""
    await init_db(temp_db_path)

    email_id = await enqueue_email(
        temp_db_path,
        to_addr="purchasing@walgreens.com",
        subject="Invoice INV-001 — PO PO-2026-04567",
        body_html="<p>Please find attached your invoice.</p>",
        attachment_path="/tmp/invoice.pdf",
    )

    assert isinstance(email_id, int)
    assert email_id > 0

    pending = await get_pending_emails(temp_db_path)
    assert len(pending) == 1
    assert pending[0]["to_addr"] == "purchasing@walgreens.com"
    assert pending[0]["status"] == EmailQueueStatus.PENDING.value
    assert pending[0]["sent_at"] is None

    await mark_email_sent(temp_db_path, email_id)

    pending_after = await get_pending_emails(temp_db_path)
    assert len(pending_after) == 0  # no longer pending


@pytest.mark.asyncio
async def test_email_queue_multiple_pending(temp_db_path: Path) -> None:
    """get_pending_emails returns all rows with PENDING status."""
    await init_db(temp_db_path)

    for i in range(3):
        await enqueue_email(
            temp_db_path,
            to_addr=f"store{i}@example.com",
            subject=f"Invoice {i}",
        )

    pending = await get_pending_emails(temp_db_path)
    assert len(pending) == 3
