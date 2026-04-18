# Hermes — Technical Architecture

## System Overview

Hermes is a local-first autonomous agent that replaces the manual
purchase-order workflow at Lowinger Distribution. It monitors an Outlook 365
inbox, parses inbound POs in any format, enters each order into the A2000 POS
system, and emails the resulting invoice back to the customer — without human
involvement on every transaction.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Emmanuel's Machine                          │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────────────────────────┐  │
│  │  start.bat   │────▶│         manager/orchestrator.py      │  │
│  │  (launcher)  │     │  ┌─────────────────────────────────┐ │  │
│  └──────────────┘     │  │          run_forever()          │ │  │
│                        │  │   cycle → cycle → cycle …      │ │  │
│  ┌──────────────┐     │  └──────────────┬────────────────┘ │  │
│  │  main.py     │     │                 │                    │  │
│  │  (banner +   │     │       ┌─────────▼──────────┐        │  │
│  │   CLI args)  │     │       │   run_cycle()       │        │  │
│  └──────────────┘     │       └──┬──────┬───────────┘        │  │
│                        │          │      │                    │  │
│  ┌──────────────┐     │   ┌──────▼──┐ ┌─▼──────────┐        │  │
│  │  .env        │─────┤   │ Email   │ │  POSAgent  │        │  │
│  │  (secrets)   │     │   │ Agent   │ │            │        │  │
│  └──────────────┘     │   └──┬──────┘ └─────┬──────┘        │  │
│                        │      │              │               │  │
│  ┌──────────────┐     │   ┌──▼──────────┐ ┌─▼──────────┐   │  │
│  │  SQLite DB   │◀────┤   │  PO Parser  │ │ A2000 Client│  │  │
│  │  (WAL mode)  │     │   │  (Ollama)   │ │ mock/api/   │  │  │
│  └──────────────┘     │   └─────────────┘ │ edi/pw      │  │  │
│                        │                   └─────────────┘  │  │
│  ┌──────────────┐     └──────────────────────────────────────┘  │
│  │  Ollama      │                                               │
│  │  (local LLM) │  ◀── qwen2.5:32b runs entirely on-device     │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                              │ IMAP/SMTP (TLS)
                    ┌─────────▼─────────┐
                    │  Outlook 365      │
                    │  Emmanuel's inbox │
                    └───────────────────┘
                              │ A2000 protocol
                    ┌─────────▼─────────┐
                    │  A2000 POS System │
                    │  (mock / api /    │
                    │   edi / playwright│
                    └───────────────────┘
```

---

## Component Descriptions

### `manager/orchestrator.py` — Orchestrator

The central coordinator. Owns the main loop (`run_forever`), advances orders
through the state machine, and handles failures by retrying or escalating.

Key methods:

| Method | Responsibility |
|--------|---------------|
| `setup()` | Initialise DB, connect email, validate A2000 |
| `run_cycle()` | One full poll-parse-enter-invoice-email pass |
| `_process_order()` | Steps 3–5 for a single order |
| `_resume_stalled_orders()` | Re-attempt orders stuck mid-pipeline |
| `handle_failures()` | Retry or escalate FAILED orders |
| `health_check()` | Return subsystem status as a dict |
| `escalate()` | Send alert email to Emmanuel |

### `agents/email_agent.py` — EmailAgent

Wraps imapclient and smtplib. Runs all I/O in a thread executor so the async
loop stays responsive. Filters inbox messages for PO-like subjects
(`po`, `purchase order`, `order #`) and PO-like attachments
(`.pdf`, `.xlsx`, `.xls`, `.csv` with recognisable filename tokens).

### `agents/pos_agent.py` — POSAgent

Validates POData, delegates to whichever A2000 adapter is active, and
coordinates status updates in the DB. Exposes `enter_order`, `retrieve_invoice`,
and `print_order`. Does not own any I/O directly — it calls through the
`A2000ClientBase` interface.

### `adapters/po_parser.py` — PO Parser

Two-stage pipeline:

1. **Format extraction** — converts raw bytes to plain text using format-specific
   extractors (pdfplumber for PDF, openpyxl for Excel, a minimal X12 850
   segment parser for EDI, regex tag-stripping for HTML, UTF-8 decode for
   everything else).
2. **LLM extraction** — sends the extracted text to a local Ollama model
   (default: qwen2.5:32b) with a zero-temperature JSON prompt. Returns a typed
   `POData` dataclass with a `list[LineItem]`.

### `adapters/a2000_client.py` — A2000 Adapters

Abstract base class `A2000ClientBase` with four concrete implementations
selected at runtime via `A2000_MODE`:

| Mode | Class | When to use |
|------|-------|-------------|
| `mock` | `MockA2000Client` | Demo, CI, development |
| `api` | `APIA2000Client` | When vendor provides REST credentials |
| `edi` | `EDIA2000Client` | AS2/VAN transmission of X12 850 documents |
| `playwright` | `PlaywrightA2000Client` | Screen automation fallback |

### `storage/db.py` — SQLite Storage

Async SQLite via `aiosqlite`. WAL journal mode for concurrent reads during
write cycles. Four tables:

| Table | Purpose |
|-------|---------|
| `orders` | One row per PO — tracks status through the pipeline |
| `order_lines` | Line items normalised out of orders |
| `audit_log` | Immutable event log for every agent action |
| `email_queue` | Outbound emails queued for delivery |

`OrderStatus` enum drives the state machine:
`RECEIVED → PARSING → PARSED → ENTERING → ENTERED → INVOICED → EMAILED`
(or `FAILED` at any step).

### `manager/config.py` — Config

Frozen dataclass populated from environment variables at import time. Fails
fast with a clear message if required variables (`EMAIL_USER`, `EMAIL_PASSWORD`)
are absent. One module-level singleton `config` imported everywhere.

---

## Data Flow Walkthrough

```
1. EMAIL_RECEIVED
   EmailAgent.poll_inbox()
   └── IMAP SEARCH UNSEEN
   └── Filter: subject tokens + attachment filename tokens
   └── Returns list of UID integers

2. PO_PARSED
   POParser.parse_and_persist(raw_email_dict)
   └── Fetch full message bytes from IMAP
   └── Walk MIME parts, extract attachments
   └── po_parser.parse_po(content_bytes, filename, content_type)
       ├── _extract_text_pdf / _excel / _edi / _html / plain
       └── _call_ollama(text) → dict
   └── storage.db.create_order(…)  → order_id (INTEGER)
   └── storage.db.create_order_line(…) × N

3. ORDER_ENTERING
   POSAgent.enter_order(order_id, a2000_client)
   └── update_order_status(ENTERING)
   └── a2000_client.create_order(po_data) → a2000_ref
   └── update_order_status(ENTERED)

4. INVOICE_RETRIEVED
   POSAgent.retrieve_invoice(order_id, a2000_client)
   └── a2000_client.get_invoice(a2000_ref) → bytes
   └── update_order_status(INVOICED)

5. INVOICE_EMAILED
   EmailAgent.send_invoice(order_id, invoice_path)
   └── smtplib STARTTLS
   └── MIMEMultipart with PDF attachment
   └── update_order_status(EMAILED)
   └── log_audit("invoice_emailed")
```

---

## Failure Modes and Recovery

| Failure point | Immediate action | Recovery |
|---------------|-----------------|---------|
| IMAP poll fails | Cycle aborts, logs exception | Retried next cycle (5-min default) |
| PO parse returns `None` | Order not created, audit logged | Manual review required |
| A2000 entry fails | `update_order_status(FAILED)` | `handle_failures()` resets to PARSED for retry; escalates after `_MAX_RETRIES` cycles |
| Invoice retrieval fails | `update_order_status(FAILED)` | Same retry/escalate flow |
| Invoice email fails | `update_order_status(FAILED)` | Same retry/escalate flow |
| Escalation email fails | Logged only (no loop risk) | Operator monitors `audit_log` |
| Process crash | SQLite WAL survives | On restart, `_resume_stalled_orders()` picks up PARSED/ENTERED orders |

All failures write a structured row to `audit_log` so Emmanuel can query the
history of any order: `SELECT * FROM audit_log WHERE details_json LIKE '%order_id%';`

---

## Why Local-First

### Security

Purchase orders contain pricing, customer data, and business volumes that are
commercially sensitive. Running everything on Emmanuel's machine means:

- PO data never leaves the premises.
- Credentials for Outlook, A2000, and the database exist only in `.env` on the
  local disk, never in a cloud secret store.
- No SaaS vendor has access to the order data or the invoice PDFs.
- Compliance with any future privacy legislation (PIPEDA, provincial) is
  straightforward: the data is on one machine, in one SQLite file.

### Reliability

No internet dependency for the core pipeline. IMAP/SMTP are the only external
calls. If the internet drops mid-cycle, the SQLite state persists and the cycle
restarts cleanly once connectivity returns.

---

## Technology Choices — Rationale

### Ollama vs Cloud LLM (OpenAI/Anthropic)

| Factor | Ollama (local) | Cloud API |
|--------|---------------|-----------|
| PO data privacy | Data never leaves machine | Data sent to vendor |
| Latency | ~5–30 s per parse (CPU/GPU) | ~1–3 s |
| Cost | Zero per-call cost | Pay-per-token |
| Offline operation | Full support | Requires internet |
| Model upgrades | Manual pull | Automatic |

qwen2.5:32b was chosen for its strong structured-extraction accuracy on
business documents. Can be swapped via `OLLAMA_MODEL` without code changes.

### SQLite vs PostgreSQL

| Factor | SQLite | PostgreSQL |
|--------|--------|------------|
| Installation | Zero (stdlib-adjacent) | Server + config |
| Concurrent writers | Single writer (fine for this use case) | Multiple |
| Backup | Copy one file | pg_dump |
| Operational complexity | None | Moderate |

Volume: tens to hundreds of orders per day. SQLite with WAL mode handles this
comfortably. Migrating to Postgres later is straightforward — the DB layer is
fully abstracted behind `storage/db.py`.

### aiosqlite vs synchronous sqlite3

The orchestrator is async to keep the main loop responsive during I/O waits
(IMAP, SMTP, HTTP to Ollama). aiosqlite provides true async SQLite without
blocking the event loop.

### imapclient vs exchangelib

exchangelib targets Exchange/EWS and requires OAuth setup or legacy auth
that Microsoft is deprecating. imapclient uses standard IMAP4, which Outlook
365 exposes on port 993 — simpler, more portable, and already working in the
demo environment.

### httpx vs requests (for Ollama)

httpx supports both sync and async. The Ollama call in `po_parser.py` is
synchronous (run in an executor), which is intentional — keeping the parser
stateless and easily testable without an event loop.
