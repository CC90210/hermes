from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OrderStatus(str, Enum):
    RECEIVED = "received"
    PARSING = "parsing"
    PARSED = "parsed"
    ENTERING = "entering"
    ENTERED = "entered"
    INVOICED = "invoiced"
    EMAILED = "emailed"
    FAILED = "failed"


class EmailQueueStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number       TEXT NOT NULL,
    customer_name   TEXT NOT NULL,
    customer_email  TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'received',
    raw_email_id    TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_lines (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku         TEXT NOT NULL,
    description TEXT,
    quantity    REAL NOT NULL,
    unit_price  REAL,
    line_total  REAL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name   TEXT NOT NULL,
    action       TEXT NOT NULL,
    details_json TEXT,
    timestamp    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    to_addr         TEXT NOT NULL,
    subject         TEXT NOT NULL,
    body_html       TEXT,
    attachment_path TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    sent_at         TEXT
);
"""


async def init_db(db_path: Path | str) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(_DDL)
        await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

async def create_order(
    db_path: Path | str,
    *,
    po_number: str,
    customer_name: str,
    customer_email: str,
    raw_email_id: str | None = None,
    status: OrderStatus = OrderStatus.RECEIVED,
) -> int:
    now = _now()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders (po_number, customer_name, customer_email, status, raw_email_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (po_number, customer_name, customer_email, status.value, raw_email_id, now, now),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def update_order_status(
    db_path: Path | str,
    order_id: int,
    status: OrderStatus,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, _now(), order_id),
        )
        await db.commit()


async def get_order(db_path: Path | str, order_id: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_orders_by_status(
    db_path: Path | str,
    status: OrderStatus,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at ASC",
            (status.value,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Order Lines
# ---------------------------------------------------------------------------

async def create_order_line(
    db_path: Path | str,
    *,
    order_id: int,
    sku: str,
    description: str | None = None,
    quantity: float,
    unit_price: float | None = None,
    line_total: float | None = None,
) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO order_lines (order_id, sku, description, quantity, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (order_id, sku, description, quantity, unit_price, line_total),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def get_order_lines(
    db_path: Path | str, order_id: int
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM order_lines WHERE order_id = ?", (order_id,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

async def log_audit(
    db_path: Path | str,
    *,
    agent_name: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO audit_log (agent_name, action, details_json, timestamp) VALUES (?, ?, ?, ?)",
            (agent_name, action, json.dumps(details) if details else None, _now()),
        )
        await db.commit()


async def get_audit_log(
    db_path: Path | str,
    *,
    agent_name: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if agent_name:
            async with db.execute(
                "SELECT * FROM audit_log WHERE agent_name = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_name, limit),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]
        async with db.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


# ---------------------------------------------------------------------------
# Email Queue
# ---------------------------------------------------------------------------

async def enqueue_email(
    db_path: Path | str,
    *,
    to_addr: str,
    subject: str,
    body_html: str | None = None,
    attachment_path: str | None = None,
) -> int:
    now = _now()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO email_queue (to_addr, subject, body_html, attachment_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (to_addr, subject, body_html, attachment_path, EmailQueueStatus.PENDING.value, now),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]


async def mark_email_sent(db_path: Path | str, email_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE email_queue SET status = ?, sent_at = ? WHERE id = ?",
            (EmailQueueStatus.SENT.value, _now(), email_id),
        )
        await db.commit()


async def mark_email_failed(db_path: Path | str, email_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE email_queue SET status = ? WHERE id = ?",
            (EmailQueueStatus.FAILED.value, email_id),
        )
        await db.commit()


async def get_pending_emails(db_path: Path | str) -> list[dict[str, Any]]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM email_queue WHERE status = ? ORDER BY created_at ASC",
            (EmailQueueStatus.PENDING.value,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]
