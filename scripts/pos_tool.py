"""pos_tool.py — Hermes A2000 POS management CLI.

Usage:
    python scripts/pos_tool.py --status <order_id>
    python scripts/pos_tool.py --list-today
    python scripts/pos_tool.py --re-run <order_id>
    python scripts/pos_tool.py --json  (add to any flag for machine output)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))


async def get_order_status(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def list_today_orders() -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def re_run_order(order_id: int) -> dict:
    """Reset a failed order to PENDING so the next cron cycle picks it up.
    Logs source=ide to the audit log for collision tracking."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return {"success": False, "error": f"Order {order_id} not found"}
        current_status = row[0]
        if current_status not in ("failed",):
            return {
                "success": False,
                "error": f"Order {order_id} is in status '{current_status}' — only 'failed' orders can be re-run",
            }
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE orders SET status = 'received', retry_count = 0, updated_at = ? WHERE id = ?",
            (now, order_id),
        )
        await db.execute(
            "INSERT INTO audit_log (agent_name, action, details_json, timestamp) VALUES (?, ?, ?, ?)",
            (
                "ide-hermes",
                "re_run_order",
                json.dumps({"order_id": order_id, "previous_status": current_status, "source": "ide"}),
                now,
            ),
        )
        await db.commit()
    return {"success": True, "order_id": order_id, "new_status": "received"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes POS tool")
    parser.add_argument("--status", type=int, metavar="ORDER_ID", help="Get order status from DB")
    parser.add_argument("--list-today", action="store_true", help="List orders from last 24h")
    parser.add_argument("--re-run", type=int, metavar="ORDER_ID", help="Re-queue a failed order")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.status:
        order = asyncio.run(get_order_status(args.status))
        if not order:
            print(f"Order {args.status} not found.", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(order, indent=2))
        else:
            print(f"Order {order['id']}: {order['po_number']} | {order['status']} | retries: {order['retry_count']}")

    elif args.list_today:
        orders = asyncio.run(list_today_orders())
        if args.as_json:
            print(json.dumps(orders, indent=2))
        else:
            print(f"=== Today's Orders ({len(orders)}) ===")
            for o in orders:
                print(f"  [{o['id']}] {o['po_number']} | {o['customer_name']} | {o['status']}")

    elif args.re_run is not None:
        result = asyncio.run(re_run_order(args.re_run))
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Order {args.re_run} reset to 'received' — will process on next cycle.")
            else:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
