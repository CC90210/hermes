"""email_tool.py — Hermes email operations CLI.

Usage:
    python scripts/email_tool.py --list-inbox
    python scripts/email_tool.py --list-drafts
    python scripts/email_tool.py --show-draft <draft_id>
    python scripts/email_tool.py --send-draft <draft_id>   # requires --confirm
    python scripts/email_tool.py --json  (add to any flag for machine output)

Note: --send-draft requires --confirm to prevent accidental sends.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

DRAFTS_DIR = _REPO_ROOT / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


def list_drafts() -> list[dict]:
    drafts = []
    for f in sorted(DRAFTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["draft_id"] = f.stem
            drafts.append(data)
        except json.JSONDecodeError:
            pass
    return drafts


def show_draft(draft_id: str) -> dict | None:
    path = DRAFTS_DIR / f"{draft_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["draft_id"] = draft_id
    return data


def send_draft(draft_id: str) -> dict:
    """Send a saved draft via SMTP. Requires EMAIL_* env vars."""
    draft = show_draft(draft_id)
    if not draft:
        return {"success": False, "error": f"Draft '{draft_id}' not found"}

    smtp_host = os.getenv("EMAIL_SMTP_HOST")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    email_user = os.getenv("EMAIL_USERNAME")
    email_pass = os.getenv("EMAIL_PASSWORD")
    from_addr = os.getenv("EMAIL_FROM", email_user or "")

    if not all([smtp_host, email_user, email_pass]):
        return {
            "success": False,
            "error": "Missing EMAIL_SMTP_HOST, EMAIL_USERNAME, or EMAIL_PASSWORD in .env",
        }

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart("alternative")
    msg["Subject"] = draft.get("subject", "(no subject)")
    msg["From"] = from_addr
    msg["To"] = draft.get("to", "")

    body = draft.get("body", "")
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:  # type: ignore[arg-type]
            server.ehlo()
            server.starttls()
            server.login(email_user, email_pass)  # type: ignore[arg-type]
            server.sendmail(from_addr, draft["to"], msg.as_string())

        sent_path = DRAFTS_DIR / f"{draft_id}.json"
        data = json.loads(sent_path.read_text(encoding="utf-8"))
        data["sent_at"] = datetime.now(timezone.utc).isoformat()
        data["status"] = "sent"
        sent_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return {"success": True, "draft_id": draft_id, "to": draft["to"]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def list_inbox() -> list[dict]:
    """List unread emails from configured inbox using IMAP."""
    imap_host = os.getenv("EMAIL_IMAP_HOST")
    email_user = os.getenv("EMAIL_USERNAME")
    email_pass = os.getenv("EMAIL_PASSWORD")

    if not all([imap_host, email_user, email_pass]):
        return [{"error": "Missing EMAIL_IMAP_HOST, EMAIL_USERNAME, or EMAIL_PASSWORD in .env"}]

    try:
        import imapclient  # type: ignore[import-untyped]

        with imapclient.IMAPClient(imap_host, ssl=True) as client:  # type: ignore[attr-defined]
            client.login(email_user, email_pass)
            client.select_folder("INBOX")
            uids = client.search(["UNSEEN"])
            if not uids:
                return []
            messages = client.fetch(uids[:20], ["ENVELOPE"])
            results = []
            for uid, data in messages.items():
                envelope = data.get(b"ENVELOPE")
                if envelope:
                    subject = envelope.subject.decode("utf-8", errors="replace") if envelope.subject else ""
                    sender = ""
                    if envelope.from_:
                        f = envelope.from_[0]
                        sender = f"{f.name or b''} <{f.mailbox or b''}@{f.host or b''}>".decode(
                            "utf-8", errors="replace"
                        ) if isinstance(f.name or b"", bytes) else str(f)
                    results.append({"uid": uid, "subject": subject, "from": sender})
            return results
    except Exception as exc:
        return [{"error": str(exc)}]


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes email tool")
    parser.add_argument("--list-inbox", action="store_true", help="List unread inbox messages")
    parser.add_argument("--list-drafts", action="store_true", help="List saved drafts")
    parser.add_argument("--show-draft", metavar="DRAFT_ID", help="Show a draft by ID")
    parser.add_argument("--send-draft", metavar="DRAFT_ID", help="Send a draft (requires --confirm)")
    parser.add_argument("--confirm", action="store_true", help="Required to actually send email")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    if args.list_inbox:
        msgs = list_inbox()
        if args.as_json:
            print(json.dumps(msgs, indent=2))
        else:
            print(f"=== Inbox Unread ({len(msgs)}) ===")
            for m in msgs:
                if "error" in m:
                    print(f"  Error: {m['error']}", file=sys.stderr)
                else:
                    print(f"  [{m['uid']}] {m['from']} — {m['subject']}")

    elif args.list_drafts:
        drafts = list_drafts()
        if args.as_json:
            print(json.dumps(drafts, indent=2))
        else:
            print(f"=== Drafts ({len(drafts)}) ===")
            for d in drafts:
                status = d.get("status", "draft")
                print(f"  [{d['draft_id']}] To: {d.get('to','')} | {d.get('subject','')} [{status}]")

    elif args.show_draft:
        draft = show_draft(args.show_draft)
        if not draft:
            print(f"Draft '{args.show_draft}' not found.", file=sys.stderr)
            sys.exit(1)
        if args.as_json:
            print(json.dumps(draft, indent=2))
        else:
            print(f"Draft ID: {draft['draft_id']}")
            print(f"To:       {draft.get('to', '')}")
            print(f"Subject:  {draft.get('subject', '')}")
            print(f"Status:   {draft.get('status', 'draft')}")
            print(f"\n{draft.get('body', '')}")

    elif args.send_draft:
        if not args.confirm:
            print("Add --confirm to actually send. This prevents accidental sends.", file=sys.stderr)
            sys.exit(1)
        result = send_draft(args.send_draft)
        if args.as_json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Sent draft '{args.send_draft}' to {result['to']}")
            else:
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
