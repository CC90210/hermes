"""report_tool.py — Hermes reporting CLI.

Usage:
    python scripts/report_tool.py --status
    python scripts/report_tool.py --daily-brief
    python scripts/report_tool.py --aging
    python scripts/report_tool.py --stuck
    python scripts/report_tool.py --json  (add to any flag for machine output)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Ensure repo root is on the path so storage imports work
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.env_loader import load_env  # noqa: E402

load_env(_REPO_ROOT)

import aiosqlite  # noqa: E402 — after path setup

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))


async def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_status() -> dict:
    now = datetime.now(timezone.utc)
    cutoff_24h = (now - timedelta(hours=24)).isoformat()

    processed = await _fetch_all(
        "SELECT COUNT(*) AS cnt FROM orders WHERE status IN ('invoiced','emailed') AND updated_at >= ?",
        (cutoff_24h,),
    )
    pending = await _fetch_all(
        "SELECT COUNT(*) AS cnt FROM orders WHERE status IN ('received','parsing','parsed','entering','entered')",
    )
    failed = await _fetch_all(
        "SELECT id, po_number, customer_name, status, updated_at FROM orders WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 20",
    )
    escalations = await _fetch_all(
        "SELECT * FROM audit_log WHERE action = 'escalation' ORDER BY timestamp DESC LIMIT 10",
    )

    return {
        "processed_24h": processed[0]["cnt"] if processed else 0,
        "pending": pending[0]["cnt"] if pending else 0,
        "failed_orders": failed,
        "escalations_pending": len(escalations),
        "db_path": str(DB_PATH),
        "timestamp": now.isoformat(),
    }


async def get_daily_brief() -> dict:
    now = datetime.now(timezone.utc)
    overnight_start = (now - timedelta(hours=12)).isoformat()

    overnight_orders = await _fetch_all(
        """SELECT o.id, o.po_number, o.customer_name, o.status,
                  SUM(ol.line_total) AS order_value
           FROM orders o
           LEFT JOIN order_lines ol ON ol.order_id = o.id
           WHERE o.created_at >= ?
           GROUP BY o.id
           ORDER BY o.created_at DESC""",
        (overnight_start,),
    )
    failures = await _fetch_all(
        "SELECT id, po_number, customer_name, retry_count FROM orders WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 10",
    )
    top_customers = await _fetch_all(
        """SELECT customer_name, COUNT(*) AS orders, SUM(ol.line_total) AS total
           FROM orders o
           LEFT JOIN order_lines ol ON ol.order_id = o.id
           WHERE o.created_at >= ?
           GROUP BY customer_name
           ORDER BY total DESC
           LIMIT 3""",
        (overnight_start,),
    )
    return {
        "overnight_orders": overnight_orders,
        "failures": failures,
        "top_customers": top_customers,
        "timestamp": now.isoformat(),
    }


async def get_aging() -> dict:
    """AR aging buckets based on order creation date."""
    now = datetime.now(timezone.utc)

    def cutoff(days: int) -> str:
        return (now - timedelta(days=days)).isoformat()

    buckets: dict[str, list] = {
        "0_30": [],
        "31_60": [],
        "61_90": [],
        "90_plus": [],
    }
    rows = await _fetch_all(
        """SELECT o.id, o.po_number, o.customer_name, o.created_at,
                  SUM(ol.line_total) AS total
           FROM orders o
           LEFT JOIN order_lines ol ON ol.order_id = o.id
           WHERE o.status NOT IN ('failed')
           GROUP BY o.id""",
    )
    for row in rows:
        created = row["created_at"]
        if created >= cutoff(30):
            buckets["0_30"].append(row)
        elif created >= cutoff(60):
            buckets["31_60"].append(row)
        elif created >= cutoff(90):
            buckets["61_90"].append(row)
        else:
            buckets["90_plus"].append(row)

    return {"aging": buckets, "timestamp": now.isoformat()}


async def get_stuck() -> dict:
    """Orders stuck in non-terminal states for > 1 hour."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = await _fetch_all(
        """SELECT id, po_number, customer_name, status, retry_count, updated_at
           FROM orders
           WHERE status IN ('received','parsing','parsed','entering','entered')
             AND updated_at < ?
           ORDER BY updated_at ASC""",
        (cutoff,),
    )
    return {"stuck_orders": rows, "timestamp": datetime.now(timezone.utc).isoformat()}


def _print_status(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))
        return
    print("=== Hermes Status ===")
    print(f"Orders processed (24h): {data['processed_24h']}")
    print(f"Orders pending:         {data['pending']}")
    print(f"Failed orders:          {len(data['failed_orders'])}")
    print(f"Escalations pending:    {data['escalations_pending']}")
    if data["failed_orders"]:
        print("\nFailed order IDs (re-run with pos_tool.py --re-run <id>):")
        for o in data["failed_orders"]:
            print(f"  [{o['id']}] {o['po_number']} — {o['customer_name']} — {o['status']}")


def _print_daily_brief(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))
        return
    print("=== Daily Briefing ===")
    print(f"1. Overnight orders: {len(data['overnight_orders'])}")
    total_val = sum(o.get("order_value") or 0 for o in data["overnight_orders"])
    print(f"   Total value: ${total_val:,.2f}")
    print(f"2. Failures: {len(data['failures'])}")
    for f in data["failures"]:
        print(f"   [{f['id']}] {f['po_number']} — retried {f['retry_count']}x")
    print("3. Top customers (overnight):")
    for c in data["top_customers"]:
        print(f"   {c['customer_name']}: {c['orders']} orders — ${c.get('total') or 0:,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes report tool")
    parser.add_argument("--status", action="store_true", help="System status dashboard")
    parser.add_argument("--daily-brief", action="store_true", help="Morning briefing")
    parser.add_argument("--aging", action="store_true", help="AR aging buckets")
    parser.add_argument("--stuck", action="store_true", help="Orders stuck > 1h")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.status:
        data = asyncio.run(get_status())
        _print_status(data, args.as_json)
    elif args.daily_brief:
        data = asyncio.run(get_daily_brief())
        _print_daily_brief(data, args.as_json)
    elif args.aging:
        data = asyncio.run(get_aging())
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            aging = data["aging"]
            print("=== AR Aging ===")
            for bucket, rows in aging.items():
                label = bucket.replace("_", "-")
                total = sum(r.get("total") or 0 for r in rows)
                print(f"  {label} days: {len(rows)} orders — ${total:,.2f}")
    elif args.stuck:
        data = asyncio.run(get_stuck())
        if args.as_json:
            print(json.dumps(data, indent=2))
        else:
            rows = data["stuck_orders"]
            print(f"=== Stuck Orders ({len(rows)}) ===")
            for r in rows:
                print(f"  [{r['id']}] {r['po_number']} — {r['status']} since {r['updated_at']}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
