---
mutability: SEMI-MUTABLE
tags: [hermes, brain, agents]
---

# AGENTS — Sub-Agent Registry

> One section per agent. Keep in sync with actual code when adding methods.

## Registry (quick reference)

| Agent | File | Role | Phase |
|-------|------|------|-------|
| Orchestrator | `manager/orchestrator.py` | Central coordinator, pipeline driver | 1 (live) |
| EmailAgent | `agents/email_agent.py` | IMAP polling + SMTP delivery | 1 (live) |
| POParser | `adapters/po_parser.py` | Format detection + LLM extraction + persist | 1 (live) |
| POSAgent | `agents/pos_agent.py` | A2000 order entry + invoice retrieval | 1 (live) |
| PhoneAgent | `agents/phone_agent.py` | IVR navigation for outbound calls | 2 (stub) |

---

## Orchestrator

**File:** `manager/orchestrator.py`

**Role:** Owns the full automation pipeline. The only component that calls other agents.
Holds references to EmailAgent, POParser, POSAgent, and the active A2000 client.

**Public Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `setup` | `async () → None` | Init DB, connect email, validate A2000 |
| `run_cycle` | `async () → dict` | One full pass: poll → parse → enter → invoice → deliver |
| `handle_failures` | `async () → None` | Review FAILED orders: retry or escalate |
| `health_check` | `async () → dict` | Returns subsystem status dict |
| `escalate` | `async (message: str) → None` | Send HTML alert email to ESCALATION_EMAIL |
| `run_forever` | `async (interval_seconds: int) → None` | Loop with SIGINT-safe shutdown |

**Dependencies:** EmailAgent, POParser, POSAgent, A2000ClientBase, storage.db, manager.config

---

## EmailAgent

**File:** `agents/email_agent.py`

**Role:** Owns all inbound and outbound email operations. Stateless apart from the
`_imap` connection handle. All actions logged to audit_log.

**Public Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `connect` | `async () → None` | Open IMAP connection to inbox |
| `is_connected` | `async () → bool` | True if _imap handle exists |
| `poll_inbox` | `async () → list[dict]` | Search UNSEEN, return PO-candidate email dicts |
| `send_invoice` | `async (to, subject, body, attachment, filename) → None` | SMTP send with PDF attachment |
| `send_alert` | `async (to_addr, subject, body_html) → None` | SMTP HTML alert |
| `run_cycle` | `async () → None` | Standalone single-agent cycle (dev use) |

**Email dict shape returned by `poll_inbox`:**
```python
{
    "uid": str,
    "subject": str,
    "from": str,
    "body": str,                              # plain text only
    "attachments": [(filename, content_type, bytes), ...]
}
```

**Dependencies:** imapclient, smtplib, storage.db, manager.config

---

## POParser

**File:** `adapters/po_parser.py`

**Role:** Adapter module that acts as an agent. Handles all PO format detection,
text extraction, LLM calling, and persistence. Lives in `adapters/` because it
wraps the Ollama inference backend, not because it is passive infrastructure.

**Public Interface:**

| Symbol | Type | Description |
|--------|------|-------------|
| `POData` | dataclass | Structured PO representation |
| `LineItem` | dataclass | Single line item within a PO |
| `parse_po(content, filename, content_type)` | function | Parse bytes → POData |
| `validate_po(po)` | function | Returns list of validation error strings |
| `POParser` | class | Stateful wrapper for orchestrator use |
| `POParser.parse_and_persist(raw_email)` | async method | Parse + write to DB, return order_id |

**Format detection priority:** filename extension → content_type → plain text fallback.

**Supported formats:** PDF, Excel (.xlsx/.xls), EDI X12 850, HTML, plain text.

**Dependencies:** pdfplumber, openpyxl, httpx (Ollama), storage.db

---

## POSAgent

**File:** `agents/pos_agent.py`

**Role:** Bridges the DB and the A2000 client. Reconstructs POData from DB rows
(does not accept POData directly — enforces DB as single source of truth), submits
to A2000, saves invoices to disk, and logs all actions.

**Public Methods:**

| Method | Signature | Description |
|--------|-----------|-------------|
| `enter_order` | `async (order_id, a2000_client) → None` | Validate, enter, log. Raises on failure. |
| `retrieve_invoice` | `async (order_id, a2000_client) → Path` | Fetch PDF bytes, save to disk, return Path |
| `print_order` | `async (order_id, a2000_client) → bool` | Send print command (legacy compat) |

**Invoice storage path:** `{LOG_DIR}/invoices/{order_id}.pdf`

**Dependencies:** storage.db, adapters.po_parser.POData, manager.config, A2000ClientBase

---

## PhoneAgent (Phase 2)

**File:** `agents/phone_agent.py`

**Role:** Outbound IVR navigation for stores that do not support email or EDI.
Placeholder only — not usable until Twilio/Vapi credentials and IVR decision trees
are collected from the client.

**Prerequisites before implementing:**
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` in `.env`
- IVR decision trees for each target store (provided by client)
- Legal review of call recording consent requirements

**Dependencies (Phase 2):** Twilio or Vapi SDK

---

## Obsidian Links
- [[brain/HERMES]] | [[brain/ARCHITECTURE]] | [[brain/CAPABILITIES]]
