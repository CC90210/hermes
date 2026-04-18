---
tags: [hermes, brain]
---

# PRINCIPLES — Hermes Operating Principles

> Read this before making non-trivial changes to the codebase.
> Each principle has a WHY and a HOW IT SHOWS UP IN CODE.

---

## 1. Local-First

**Why:** Hermes processes real business documents — purchase orders, invoices, customer
addresses, pricing. This data belongs to the client. No cloud AI, no SaaS pipeline,
no third-party data processor should ever touch it.

**How it shows up in code:**
- `OLLAMA_HOST` defaults to `http://localhost:11434`. All LLM calls go there.
- No imports from `openai`, `anthropic`, or any cloud inference SDK.
- The only external calls are to the client's own email server and A2000 instance.
- If you see a cloud AI import in a PR, reject it.

---

## 2. Idempotent by Design

**Why:** Email is unreliable. Networks retry. Operators restart processes. Hermes
must never enter the same purchase order twice — a duplicate order causes real
financial harm to the client.

**How it shows up in code:**
- `poll_inbox()` searches `UNSEEN` only — already-seen emails are skipped by the IMAP server.
- UID tracking: each email's IMAP UID is stored as `raw_email_id` on the orders row.
- `create_order()` in `storage/db.py` — before persisting, callers can check for existing
  `raw_email_id` to prevent duplicate rows.
- The parser stores the UID on parse; if the orchestrator sees the same UID twice, it
  already has an `order_id` and skips re-parsing.

---

## 3. Fail-Stopped, Not Fail-Open

**Why:** A partial order entry is worse than no order entry. If Hermes is uncertain,
entering bad data into A2000 wastes the client's time and risks shipping errors.
Silence is worse than an alert.

**How it shows up in code:**
- `validate_po()` in `adapters/po_parser.py` returns a list of errors; on any error,
  the order status is set to `FAILED` and an escalation is sent.
- `_MAX_RETRIES = 3` in the Orchestrator — after 3 failures, the order escalates, it
  does NOT retry silently forever.
- Every `except` block in the pipeline either logs + escalates or re-raises — none
  swallow errors silently.

---

## 4. Audit Everything

**Why:** The client needs to trust that Hermes did what it says it did. Regulators,
auditors, and disputes all require a defensible paper trail. Hermes must be
completely auditable at any point in time.

**How it shows up in code:**
- Every agent action that changes external state calls `log_audit()` before AND
  after the action where applicable.
- The `audit_log` table is append-only — no UPDATE or DELETE operations.
- Log format enforced in `CLAUDE.md`: `YYYY-MM-DD HH:MM:SS | {agent} | {action} | {result}`
- The storage layer never truncates `audit_log` regardless of size.

---

## 5. Escalate, Don't Guess

**Why:** Hermes is not authorized to make business decisions. If a PO is ambiguous,
entering a best guess can cause real financial damage — wrong quantities shipped,
wrong customer billed. The right move is always to pause and ask.

**How it shows up in code:**
- `POSAgent.enter_order()` calls `_validate_po()` before touching A2000 — missing
  `po_number` or empty `line_items` are hard stops.
- `Orchestrator.escalate()` sends a structured HTML email to `ESCALATION_EMAIL`.
- The escalation message includes the PO number, customer, internal order_id, and
  a specific description of what is wrong — not a vague "something failed".
- Parser confidence is implicit in Ollama temperature=0.0 — deterministic extraction,
  no hallucinated values.

---

## 6. Stateless Sub-Agents

**Why:** Agents that carry state in memory are fragile — a restart loses the state,
two instances diverge, and debugging becomes harder. SQLite is the single source
of truth. Agents are replaceable components that read and write through storage.

**How it shows up in code:**
- `POSAgent.enter_order()` accepts an `order_id` and re-reads POData from DB — it
  does not accept a POData argument. The DB is always authoritative.
- `EmailAgent` holds only one stateful thing: the `_imap` connection handle, which
  is re-created on `connect()`. All business state lives in the DB.
- Agents do not import each other. The Orchestrator wires them together.
- If an agent module is replaced, the DB schema and audit contract remain intact.

---

## Obsidian Links
- [[brain/HERMES]] | [[brain/ARCHITECTURE]] | [[brain/AGENTS]]
