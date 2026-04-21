"""chargeback_tool.py — Hermes chargeback tracking CLI.

Reads from the chargeback_tracker adapter (adapters/chargeback_tracker.py) and
the SQLite DB. Chargebacks are stored in a JSON sidecar file since the current
DB schema does not have a chargebacks table.

Usage:
    python scripts/chargeback_tool.py --list-open
    python scripts/chargeback_tool.py --add
    python scripts/chargeback_tool.py --show <cb_id>
    python scripts/chargeback_tool.py --draft-dispute <cb_id>
    python scripts/chargeback_tool.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

DRAFTS_DIR = _REPO_ROOT / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)

# Chargeback sidecar data store
CB_FILE = _REPO_ROOT / "storage" / "chargebacks.json"


def _load_chargebacks() -> list[dict]:
    if not CB_FILE.exists():
        return []
    try:
        return json.loads(CB_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save_chargebacks(data: list[dict]) -> None:
    CB_FILE.parent.mkdir(parents=True, exist_ok=True)
    CB_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_open() -> list[dict]:
    all_cb = _load_chargebacks()
    now = datetime.now(timezone.utc)
    result = []
    for cb in all_cb:
        if cb.get("status") in ("resolved", "won", "lost"):
            continue
        dispute_deadline = cb.get("dispute_deadline")
        days_remaining = None
        urgent = False
        if dispute_deadline:
            deadline_dt = datetime.fromisoformat(dispute_deadline)
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
            days_remaining = (deadline_dt - now).days
            urgent = days_remaining < 7
        result.append({**cb, "days_remaining": days_remaining, "urgent": urgent})
    return sorted(result, key=lambda x: x.get("days_remaining") or 9999)


def get_chargeback(cb_id: str) -> dict | None:
    for cb in _load_chargebacks():
        if cb.get("id") == cb_id:
            return cb
    return None


def add_chargeback_interactive() -> dict:
    print("=== Add Chargeback ===")
    retailer = input("Retailer: ").strip()
    amount_str = input("Amount ($): ").strip()
    po_number = input("PO Number (optional): ").strip()
    invoice_number = input("Invoice Number (optional): ").strip()
    reason = input("Reason code / description: ").strip()
    deadline_str = input("Dispute deadline (YYYY-MM-DD): ").strip()

    try:
        amount = float(amount_str)
    except ValueError:
        print("Invalid amount.", file=sys.stderr)
        sys.exit(1)

    cb_id = f"CB-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    cb = {
        "id": cb_id,
        "retailer": retailer,
        "amount": amount,
        "po_number": po_number,
        "invoice_number": invoice_number,
        "reason": reason,
        "dispute_deadline": deadline_str,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    cbs = _load_chargebacks()
    cbs.append(cb)
    _save_chargebacks(cbs)
    print(f"Chargeback {cb_id} added.")
    return cb


def draft_dispute(cb_id: str) -> str:
    cb = get_chargeback(cb_id)
    if not cb:
        return f"Chargeback '{cb_id}' not found."

    draft_body = f"""Subject: Dispute for Chargeback {cb_id} — {cb.get('retailer', '')}

Dear Accounts Payable Team,

We are writing to formally dispute the chargeback referenced above.

Chargeback ID:   {cb['id']}
Retailer:        {cb.get('retailer', '')}
Amount:          ${cb.get('amount', 0):,.2f}
PO Number:       {cb.get('po_number', 'N/A')}
Invoice Number:  {cb.get('invoice_number', 'N/A')}
Reason:          {cb.get('reason', '')}

Please find attached the supporting documentation demonstrating that this shipment
was delivered in full compliance with your requirements. We request that this
chargeback be reversed.

Please respond within 5 business days.

— Emmanuel Lowinger
Lowinger Distribution
"""

    draft_id = f"dispute_{cb_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    path = DRAFTS_DIR / f"{draft_id}.json"
    path.write_text(
        json.dumps(
            {
                "to": f"ap@{cb.get('retailer', 'retailer').lower().replace(' ', '')}.com (update before sending)",
                "subject": f"Dispute for Chargeback {cb_id} — {cb.get('retailer', '')}",
                "body": draft_body,
                "chargeback_id": cb_id,
                "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return draft_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes chargeback tool")
    parser.add_argument("--list-open", action="store_true", help="List open chargebacks")
    parser.add_argument("--add", action="store_true", help="Add a new chargeback interactively")
    parser.add_argument("--show", metavar="CB_ID", help="Show a chargeback by ID")
    parser.add_argument("--draft-dispute", metavar="CB_ID", help="Draft a dispute email for a chargeback")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.list_open:
        chargebacks = list_open()
        total = sum(cb.get("amount", 0) for cb in chargebacks)
        if args.as_json:
            print(json.dumps({"chargebacks": chargebacks, "total": total}, indent=2))
        else:
            print(f"=== Open Chargebacks ({len(chargebacks)}) — Total: ${total:,.2f} ===")
            for cb in chargebacks:
                days = cb.get("days_remaining")
                days_label = f"{days}d remaining" if days is not None else "no deadline set"
                urgent = " [URGENT]" if cb.get("urgent") else ""
                print(f"  [{cb['id']}] {cb.get('retailer','')} | ${cb.get('amount',0):,.2f} | {days_label}{urgent}")
                print(f"    Reason: {cb.get('reason','')}")

    elif args.add:
        result = add_chargeback_interactive()
        if args.as_json:
            print(json.dumps(result, indent=2))

    elif args.show:
        cb = get_chargeback(args.show)
        if not cb:
            print(f"Chargeback '{args.show}' not found.", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(cb, indent=2))
        else:
            print(f"=== {cb['id']} ===")
            for k, v in cb.items():
                print(f"  {k}: {v}")

    elif args.draft_dispute:
        draft_id = draft_dispute(args.draft_dispute)
        if args.as_json:
            print(json.dumps({"draft_id": draft_id}, indent=2))
        else:
            print(f"Dispute draft saved: drafts/{draft_id}.json")
            print("Review and send with: python scripts/email_tool.py --send-draft " + draft_id + " --confirm")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
