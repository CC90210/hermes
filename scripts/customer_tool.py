"""customer_tool.py — Hermes customer lookup CLI.

Usage:
    python scripts/customer_tool.py --lookup "Walgreens"
    python scripts/customer_tool.py --lookup "walgreens@example.com"
    python scripts/customer_tool.py --list
    python scripts/customer_tool.py --history <customer_name> --days 90
    python scripts/customer_tool.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.env_loader import load_env  # noqa: E402

load_env(_REPO_ROOT)

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))


async def lookup_customer(query: str) -> dict:
    """Search by name (partial match) or exact email."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        like = f"%{query}%"
        async with db.execute(
            """SELECT customer_name, customer_email,
                      COUNT(*) AS total_orders,
                      SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_orders,
                      SUM(CASE WHEN status IN ('invoiced','emailed') THEN 1 ELSE 0 END) AS completed_orders,
                      MAX(created_at) AS last_order_at
               FROM orders
               WHERE customer_name LIKE ? OR customer_email = ?
               GROUP BY customer_name, customer_email
               ORDER BY last_order_at DESC
               LIMIT 5""",
            (like, query),
        ) as cur:
            customers = [dict(r) for r in await cur.fetchall()]

        if not customers:
            return {"found": False, "query": query}

        # Get most recent orders for the top match
        top = customers[0]
        async with db.execute(
            """SELECT o.id, o.po_number, o.status, o.created_at, SUM(ol.line_total) AS order_value
               FROM orders o
               LEFT JOIN order_lines ol ON ol.order_id = o.id
               WHERE o.customer_name = ?
               GROUP BY o.id
               ORDER BY o.created_at DESC
               LIMIT 10""",
            (top["customer_name"],),
        ) as cur:
            recent_orders = [dict(r) for r in await cur.fetchall()]

        top["recent_orders"] = recent_orders
        return {"found": True, "customers": customers, "detail": top}


async def list_all_customers() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT customer_name, customer_email,
                      COUNT(*) AS total_orders,
                      MAX(created_at) AS last_order_at
               FROM orders
               GROUP BY customer_name, customer_email
               ORDER BY last_order_at DESC"""
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def order_history(customer_name: str, days: int = 90) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT o.id, o.po_number, o.status, o.created_at, o.retry_count,
                      SUM(ol.line_total) AS order_value
               FROM orders o
               LEFT JOIN order_lines ol ON ol.order_id = o.id
               WHERE o.customer_name LIKE ? AND o.created_at >= ?
               GROUP BY o.id
               ORDER BY o.created_at DESC""",
            (f"%{customer_name}%", cutoff),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes customer tool")
    parser.add_argument("--lookup", metavar="QUERY", help="Look up customer by name or email")
    parser.add_argument("--list", action="store_true", help="List all known customers")
    parser.add_argument("--history", metavar="NAME", help="Show order history for a customer")
    parser.add_argument("--days", type=int, default=90, help="History window in days (default: 90)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.lookup:
        result = asyncio.run(lookup_customer(args.lookup))
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if not result["found"]:
                print(f"No customer found matching '{args.lookup}'")
                sys.exit(1)
            detail = result["detail"]
            print(f"=== {detail['customer_name']} ===")
            print(f"Email:      {detail['customer_email']}")
            print(f"Total POs:  {detail['total_orders']}")
            print(f"Completed:  {detail['completed_orders']}")
            print(f"Failed:     {detail['failed_orders']}")
            print(f"Last order: {detail['last_order_at']}")
            if detail.get("recent_orders"):
                print("\nRecent Orders:")
                for o in detail["recent_orders"][:5]:
                    val = o.get("order_value") or 0
                    print(f"  [{o['id']}] {o['po_number']} | {o['status']} | ${val:,.2f} | {o['created_at'][:10]}")

    elif args.list:
        customers = asyncio.run(list_all_customers())
        if args.as_json:
            print(json.dumps(customers, indent=2))
        else:
            print(f"=== Customers ({len(customers)}) ===")
            for c in customers:
                print(f"  {c['customer_name']} | {c['total_orders']} orders | last: {c['last_order_at'][:10]}")

    elif args.history:
        orders = asyncio.run(order_history(args.history, args.days))
        if args.as_json:
            print(json.dumps(orders, indent=2))
        else:
            print(f"=== {args.history} — Last {args.days} Days ({len(orders)} orders) ===")
            for o in orders:
                val = o.get("order_value") or 0
                print(f"  [{o['id']}] {o['po_number']} | {o['status']} | ${val:,.2f} | {o['created_at'][:10]}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
