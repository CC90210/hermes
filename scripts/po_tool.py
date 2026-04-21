"""po_tool.py — Hermes PO management CLI.

Usage:
    python scripts/po_tool.py --list
    python scripts/po_tool.py --list --status failed
    python scripts/po_tool.py --show <order_id>
    python scripts/po_tool.py --parse <file_path>
    python scripts/po_tool.py --json  (add to any flag for machine output)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))


async def list_orders(status: str | None = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            query = "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT 100"
            async with db.execute(query, (status,)) as cur:
                return [dict(r) for r in await cur.fetchall()]
        query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT 100"
        async with db.execute(query) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def show_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            order = dict(row)
        async with db.execute(
            "SELECT * FROM order_lines WHERE order_id = ?", (order_id,)
        ) as cur:
            order["lines"] = [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            "SELECT * FROM audit_log WHERE details_json LIKE ? ORDER BY timestamp DESC LIMIT 20",
            (f'%"order_id": {order_id}%',),
        ) as cur:
            order["audit"] = [dict(r) for r in await cur.fetchall()]
    return order


async def parse_file(file_path: str) -> dict:
    """Parse a PO file using the pipeline parser and return extracted data without persisting."""
    from adapters.po_parser import POParser

    parser = POParser()
    po_data = await parser.parse(Path(file_path))
    return {
        "po_number": po_data.po_number,
        "customer_name": po_data.customer_name,
        "customer_email": po_data.customer_email,
        "ship_date": po_data.ship_date,
        "line_items": [
            {
                "sku": li.sku,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
            }
            for li in po_data.line_items
        ],
        "raw_file": str(file_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes PO tool")
    parser.add_argument("--list", action="store_true", help="List orders")
    parser.add_argument("--status", help="Filter by status (with --list)")
    parser.add_argument("--show", type=int, metavar="ORDER_ID", help="Show order details")
    parser.add_argument("--parse", metavar="FILE", help="Parse a PO file (no DB write)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.list:
        orders = asyncio.run(list_orders(args.status))
        if args.as_json:
            print(json.dumps(orders, indent=2))
        else:
            print(f"=== Orders ({len(orders)}) ===")
            for o in orders:
                print(f"  [{o['id']}] {o['po_number']} | {o['customer_name']} | {o['status']} | {o['created_at'][:10]}")

    elif args.show:
        order = asyncio.run(show_order(args.show))
        if not order:
            print(f"Order {args.show} not found.", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(order, indent=2))
        else:
            print(f"=== Order {order['id']} ===")
            print(f"PO:       {order['po_number']}")
            print(f"Customer: {order['customer_name']} <{order['customer_email']}>")
            print(f"Status:   {order['status']}")
            print(f"Retries:  {order['retry_count']}")
            print(f"Created:  {order['created_at']}")
            if order.get("lines"):
                print(f"\nLine Items ({len(order['lines'])}):")
                for line in order["lines"]:
                    print(f"  {line['sku']} x{line['quantity']} @ ${line.get('unit_price') or 0:.2f} = ${line.get('line_total') or 0:.2f}")

    elif args.parse:
        try:
            data = asyncio.run(parse_file(args.parse))
        except Exception as exc:
            print(f"Parse error: {exc}", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            print(f"PO Number:  {data['po_number']}")
            print(f"Customer:   {data['customer_name']} <{data['customer_email']}>")
            print(f"Ship Date:  {data.get('ship_date', 'not found')}")
            print(f"Line Items: {len(data['line_items'])}")
            for li in data["line_items"]:
                print(f"  {li['sku']} x{li['quantity']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
