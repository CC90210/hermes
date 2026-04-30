"""invoice_tool.py — Hermes invoice management CLI.

Usage:
    python scripts/invoice_tool.py --list
    python scripts/invoice_tool.py --list --order-id <id>
    python scripts/invoice_tool.py --resend <order_id>     # requires --confirm
    python scripts/invoice_tool.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.env_loader import load_env  # noqa: E402

load_env(_REPO_ROOT)

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))


async def list_invoices(order_id: int | None = None) -> list[dict]:
    """List emailed invoices from the email_queue table."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if order_id:
            async with db.execute(
                "SELECT * FROM email_queue WHERE attachment_path LIKE ? ORDER BY created_at DESC",
                (f"%order_{order_id}%",),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            "SELECT * FROM email_queue WHERE attachment_path IS NOT NULL ORDER BY created_at DESC LIMIT 50"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_order_for_resend(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def resend_invoice(order_id: int) -> dict:
    """Re-queue an invoice email for an invoiced order."""
    order = await get_order_for_resend(order_id)
    if not order:
        return {"success": False, "error": f"Order {order_id} not found"}
    if order["status"] not in ("invoiced", "emailed"):
        return {
            "success": False,
            "error": f"Order {order_id} has status '{order['status']}' — can only resend for invoiced/emailed orders",
        }
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO email_queue (to_addr, subject, body_html, status, created_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (
                order["customer_email"],
                f"Invoice for PO {order['po_number']} (resent)",
                f"<p>Hi {order['customer_name']},</p><p>Please find the invoice for PO {order['po_number']} attached.</p><p>— Hermes</p>",
                now,
            ),
        )
        await db.execute(
            "INSERT INTO audit_log (agent_name, action, details_json, timestamp) VALUES (?, ?, ?, ?)",
            (
                "ide-hermes",
                "resend_invoice",
                json.dumps({"order_id": order_id, "source": "ide"}),
                now,
            ),
        )
        await db.commit()
    return {"success": True, "order_id": order_id, "to": order["customer_email"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes invoice tool")
    parser.add_argument("--list", action="store_true", help="List invoices")
    parser.add_argument("--order-id", type=int, help="Filter by order ID (use with --list)")
    parser.add_argument("--resend", type=int, metavar="ORDER_ID", help="Resend invoice for an order")
    parser.add_argument("--confirm", action="store_true", help="Required to actually resend")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.list:
        invoices = asyncio.run(list_invoices(args.order_id))
        if args.as_json:
            print(json.dumps(invoices, indent=2))
        else:
            print(f"=== Invoices ({len(invoices)}) ===")
            for i in invoices:
                print(f"  [{i['id']}] To: {i['to_addr']} | {i['subject']} | {i['status']}")

    elif args.resend is not None:
        if not args.confirm:
            print("Add --confirm to actually resend the invoice.", file=sys.stderr)
            sys.exit(1)
        result = asyncio.run(resend_invoice(args.resend))
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Invoice for order {args.resend} queued to {result['to']}")
            else:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
