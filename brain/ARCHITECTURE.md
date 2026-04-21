---
mutability: SEMI-MUTABLE
tags: [hermes, brain, architecture]
---

# ARCHITECTURE — Hermes Technical System

> How Hermes understands its own structure. Agent-perspective view of the system.

## System Overview

Hermes is a single-tenant Python process that runs on the client's machine. It contains
no cloud AI calls, no shared database, and no multi-tenant state. Each deployment is
fully isolated.

```
main.py
  └── cron/scheduler.py             CLI entrypoint — argument parsing, loop timing
        └── manager/orchestrator.py  Central coordinator — owns the pipeline
              ├── agents/email_agent.py      Inbox polling + outbound SMTP
              ├── adapters/po_parser.py      Format detection + LLM extraction
              ├── agents/pos_agent.py        A2000 order entry + invoice retrieval
              └── adapters/a2000_*.py        Four-mode adapter ladder
                    ├── a2000_mock.py        Mock (dev/demo)
                    ├── a2000_api.py         REST API (Tier 1)
                    ├── a2000_edi.py         EDI X12 850 (Tier 2)
                    └── a2000_playwright.py  Browser automation (Tier 4)
```

State lives entirely in `storage/db.py` (SQLite). Agents are stateless — they
read and write through storage functions. The Orchestrator is the only component
that calls agents directly.

## The 5-Stage Pipeline

| Stage | Owner | Input | Output | DB Status |
|-------|-------|-------|--------|-----------|
| 1. Detect | EmailAgent | IMAP UNSEEN search | Raw email dicts | — |
| 2. Parse | POParser (adapter) | Raw email dict | POData + order_lines rows | PARSED |
| 3. Enter | POSAgent + A2000Client | order_id | A2000 confirmation | ENTERED |
| 4. Invoice | POSAgent + A2000Client | order_id | PDF bytes on disk | INVOICED |
| 5. Deliver | EmailAgent | invoice PDF path | Sent SMTP email | EMAILED |

Failure at any stage sets status = FAILED. The Orchestrator retries up to 3 times,
then escalates to the operator via email.

## Sub-Agent Responsibilities

**EmailAgent** (`agents/email_agent.py`)
- Owns all IMAP and SMTP operations
- Detects PO candidates from subject tokens and attachment filenames
- Returns raw email dicts — never parses content
- Also sends invoices and alert escalations

**POParser** (`adapters/po_parser.py`)
- Detects format: PDF → pdfplumber, Excel → openpyxl, EDI → custom X12 parser, plain text passthrough
- Sends extracted text to Ollama with a structured JSON prompt
- Returns `POData` dataclass + validates required fields
- Persists order + order_lines to SQLite

**POSAgent** (`agents/pos_agent.py`)
- Reconstructs `POData` from DB (does not receive it directly — avoids tight coupling)
- Delegates `create_order()` and `get_invoice()` calls to whichever A2000 client is active
- Writes invoice PDF bytes to `logs/invoices/{order_id}.pdf`

**Orchestrator** (`manager/orchestrator.py`)
- Instantiates all agents at startup
- Selects the A2000 client via `A2000_MODE` env var
- Runs `run_cycle()` on an interval (default 300s)
- Calls `handle_failures()` after every cycle

## Adapter Pattern — A2000 Integration

All four adapters implement `A2000ClientBase` (ABC defined in `adapters/a2000_client.py`).

```
A2000ClientBase
  ├── create_order(po: POData) → OrderResult
  ├── get_order(order_id: str) → dict
  ├── get_invoice(order_id: str) → bytes
  ├── print_order(order_id: str) → bool
  ├── validate() → None          (raises on connection failure)
  └── is_reachable() → bool      (health check)
```

The Orchestrator holds one client instance. Swapping `A2000_MODE` changes the concrete
class — no other code changes required.

## Audit Log Contract

Every agent action must call `storage.db.log_audit()` with:

```python
await log_audit(
    db_path,
    agent_name="<agent_name>",   # "email_agent" | "pos_agent" | "po_parser" | "orchestrator"
    action="<verb_noun>",         # e.g. "order_entered", "invoice_retrieved", "escalation_sent"
    details={...},               # arbitrary dict — serialized to JSON
)
```

Rows are append-only and never deleted. The audit log is the ground truth for what
Hermes did and when.

## Health Check Fields

`Orchestrator.health_check()` returns:

```python
{
    "email_connected": bool,       # EmailAgent IMAP connection alive
    "a2000_reachable": bool,       # A2000Client.is_reachable()
    "pending_orders": int,         # orders with status=PARSED
    "failed_orders": int,          # orders with status=FAILED
    "cycle_count": int,            # cycles run this session
    "timestamp": str,              # ISO 8601 UTC
}
```

Exposed via `python main.py --health` (prints JSON to stdout).

## Storage Schema (summary)

| Table | Purpose |
|-------|---------|
| orders | One row per PO. Status tracks pipeline stage. |
| order_lines | Line items for each order. |
| audit_log | Append-only action log with agent, action, details, timestamp. |
| email_queue | Outbound emails queued for retry if SMTP fails. |

## Configuration Entry Point

`manager/config.py` holds the `Config` dataclass (frozen). Import the module-level
`config` singleton everywhere. Never re-instantiate `Config` in other modules.

## Obsidian Links
- [[brain/HERMES]] | [[brain/AGENTS]] | [[brain/CAPABILITIES]] | [[brain/PRINCIPLES]]
