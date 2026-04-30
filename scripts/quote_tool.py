"""quote_tool.py — Hermes quote builder CLI.

Usage:
    python scripts/quote_tool.py --customer "Walgreens" --interactive
    python scripts/quote_tool.py --list
    python scripts/quote_tool.py --show <quote_id>
    python scripts/quote_tool.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from runtime.env_loader import load_env  # noqa: E402

load_env(_REPO_ROOT)

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))
DRAFTS_DIR = _REPO_ROOT / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


async def get_customer_context(customer_query: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT customer_name, customer_email, COUNT(*) AS total_orders,
                      MAX(created_at) AS last_order_at
               FROM orders WHERE customer_name LIKE ?
               GROUP BY customer_name, customer_email
               LIMIT 1""",
            (f"%{customer_query}%",),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


def save_quote(quote_data: dict) -> str:
    """Save quote to drafts/ and return the quote ID."""
    quote_id = f"quote_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    path = DRAFTS_DIR / f"{quote_id}.json"
    path.write_text(json.dumps(quote_data, indent=2), encoding="utf-8")
    return quote_id


def list_quotes() -> list[dict]:
    quotes = []
    for f in sorted(DRAFTS_DIR.glob("quote_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["quote_id"] = f.stem
            quotes.append(data)
        except json.JSONDecodeError:
            pass
    return quotes


def show_quote(quote_id: str) -> dict | None:
    path = DRAFTS_DIR / f"{quote_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["quote_id"] = quote_id
    return data


def interactive_quote(customer_query: str) -> dict:
    """CLI-interactive quote builder. Prompts for line items."""
    ctx = asyncio.run(get_customer_context(customer_query))
    customer_name = ctx.get("customer_name", customer_query)
    customer_email = ctx.get("customer_email", "")

    print(f"\n=== Quote Builder: {customer_name} ===")
    if ctx:
        print(f"Email: {customer_email} | Past orders: {ctx.get('total_orders', 0)}")
    print("Enter line items (SKU, qty, unit price). Empty SKU to finish.\n")

    lines = []
    while True:
        sku = input("  SKU (or Enter to finish): ").strip()
        if not sku:
            break
        qty_str = input(f"  Quantity for {sku}: ").strip()
        price_str = input("  Unit price ($): ").strip()
        try:
            qty = float(qty_str)
            price = float(price_str)
            lines.append({"sku": sku, "quantity": qty, "unit_price": price, "line_total": qty * price})
            print(f"  Added: {sku} x{qty} @ ${price:.2f} = ${qty * price:.2f}")
        except ValueError:
            print("  Invalid qty or price — skipped.")

    if not lines:
        print("No line items — quote cancelled.")
        sys.exit(0)

    total = sum(li["line_total"] for li in lines)
    terms = input("\nPayment terms (default Net-30): ").strip() or "Net-30"
    notes = input("Notes (optional): ").strip()

    quote = {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "date": datetime.now(timezone.utc).isoformat()[:10],
        "payment_terms": terms,
        "line_items": lines,
        "total": total,
        "notes": notes,
        "status": "draft",
        "created_by": "ide-hermes",
    }

    quote_id = save_quote(quote)
    print(f"\nQuote saved: {quote_id}")
    print(f"Total: ${total:,.2f} | Terms: {terms}")
    print(f"File: drafts/{quote_id}.json")
    print("\nApprove and send with: python scripts/email_tool.py --send-draft <quote_id> --confirm")
    return {**quote, "quote_id": quote_id}


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes quote tool")
    parser.add_argument("--customer", metavar="QUERY", help="Customer name or ID for quote")
    parser.add_argument("--interactive", action="store_true", help="Interactive quote builder")
    parser.add_argument("--list", action="store_true", help="List saved quotes")
    parser.add_argument("--show", metavar="QUOTE_ID", help="Show a quote")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.customer and args.interactive:
        result = interactive_quote(args.customer)
        if args.as_json:
            print(json.dumps(result, indent=2))

    elif args.list:
        quotes = list_quotes()
        if args.as_json:
            print(json.dumps(quotes, indent=2))
        else:
            print(f"=== Quotes ({len(quotes)}) ===")
            for q in quotes:
                print(f"  [{q['quote_id']}] {q['customer_name']} | ${q.get('total', 0):,.2f} | {q['date']} | {q.get('status', 'draft')}")

    elif args.show:
        quote = show_quote(args.show)
        if not quote:
            print(f"Quote '{args.show}' not found.", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(quote, indent=2))
        else:
            print(f"=== Quote {quote['quote_id']} ===")
            print(f"Customer: {quote['customer_name']} <{quote.get('customer_email', '')}>")
            print(f"Date:     {quote['date']}")
            print(f"Terms:    {quote.get('payment_terms', 'Net-30')}")
            print(f"Status:   {quote.get('status', 'draft')}")
            print("\nLine Items:")
            for li in quote.get("line_items", []):
                print(f"  {li['sku']} x{li['quantity']} @ ${li['unit_price']:.2f} = ${li['line_total']:.2f}")
            print(f"\nTotal: ${quote.get('total', 0):,.2f}")
            if quote.get("notes"):
                print(f"Notes: {quote['notes']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
