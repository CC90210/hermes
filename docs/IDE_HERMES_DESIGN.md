---
tags: [hermes, design, ide-layer, emmanuel]
status: draft
author: Bravo (for CC review)
date: 2026-04-18
---

# IDE-Resident Hermes - Design Document

> Extend Hermes from a silent background pipeline into a conversational IDE teammate for Emmanuel Lowinger, using the Claude Code / Bravo pattern as the blueprint.

---

## 1. Architecture

Two layers, one brain. The **Pipeline Layer** stays exactly as it is today (Python, cron, Ollama, SQLite) - it keeps running 24/7 whether Emmanuel's laptop is open or not. The **IDE Layer** is Claude Code opened against the same Hermes repo, with a CLAUDE.md that teaches Claude to *be* Hermes.

```
+---------------------------------------------------------------+
|              EMMANUEL'S WINDOWS MACHINE                        |
|                                                                |
|  +-------------------+        +-----------------------------+ |
|  |  CLAUDE CODE IDE  |        |  BACKGROUND HERMES          | |
|  |  (interactive)    |        |  (python main.py, cron)     | |
|  |                   |        |                             | |
|  |  Model: Claude    |        |  Model: Ollama (local)      | |
|  |  API (Sonnet 4.6) |        |  Runs every 300s            | |
|  |                   |        |                             | |
|  |  Reads CLAUDE.md  |        |  Reads .env                 | |
|  |  Loads HERMES.md  |        |  Logs to audit_log          | |
|  |  Calls CLI tools  |        |  Writes to orders/invoices  | |
|  +---------+---------+        +--------------+--------------+ |
|            |                                 |                |
|            |   shared reads and writes       |                |
|            v                                 v                |
|        +-----------------------------------------+            |
|        |   storage/db.py  -->  hermes.sqlite     |            |
|        |   audit_log (append-only)               |            |
|        |   orders, invoices, customers, pos      |            |
|        |   memory/ (markdown state files)        |            |
|        +-----------------------------------------+            |
|                                                                |
+---------------------------------------------------------------+
```

**Model placement (deliberate asymmetry):**
- **Pipeline = Ollama.** Deterministic, offline, zero marginal cost, processes real customer data (PRINCIPLE 1: local-first). Never changes.
- **IDE = Claude API (Sonnet 4.6).** Reasoning quality matters more than data sensitivity. Emmanuel's conversational queries don't send customer data to Anthropic unless he explicitly pastes it. All business data reads happen locally via CLI tools that Claude orchestrates but never sees directly.

**Communication:** The two layers never call each other. They communicate exclusively through the SQLite DB and the filesystem (`memory/`, `audit_log`). This is the same pattern as Bravo + background cron jobs today.

---

## 2. Directory Structure

**Already at** `C:\Users\User\APPS\hermes`: `main.py`, `agents/`, `adapters/`, `manager/`, `storage/`, `cron/`, `brain/` (HERMES, ARCHITECTURE, AGENTS, CAPABILITIES, PRINCIPLES), `skills/` (6 pipeline skills), `clients/`, `tests/`, `demo/`, `docs/`, `CLAUDE.md`, `AGENTS.md`.

**New additions for the IDE layer:**

```
hermes/
    CLAUDE.md                      # REWRITE - interactive rules (see section 3)
    brain/
        EMMANUEL.md                # NEW - client profile (like USER.md in Bravo)
        STATE.md                   # NEW - ephemeral operational state
        QUICK_REFERENCE.md         # NEW - intent to CLI tool routing table
        (HERMES.md, PRINCIPLES.md, etc. - unchanged)
    memory/
        ACTIVE_TASKS.md            # NEW - open items across sessions
        SESSION_LOG.md             # NEW - 1-2 line summary per session
        MISTAKES.md                # NEW - Emmanuel corrections, never repeat
        PATTERNS.md                # NEW - validated approaches
        DECISIONS.md               # NEW - business rules Emmanuel locks in
    skills/
        (10-15 new interactive skills - see section 4)
    scripts/                       # NEW DIRECTORY - CLI wrappers (see section 5)
        email_tool.py
        pos_tool.py
        po_tool.py
        invoice_tool.py
        customer_tool.py
        report_tool.py
        health_tool.py
        state_sync.py
    .claude/
        settings.local.json        # NEW - hooks (block .env writes, audit bash ops)
    onboarding/
        EMMANUEL_DAY1.md           # NEW - 7-step setup guide
```

No code moves. Pipeline code is untouched. Everything new is read-only scaffolding for the IDE layer or thin CLI wrappers around existing modules.

---

## 3. CLAUDE.md for Emmanuel's Hermes

~~~markdown
# CLAUDE CODE - HERMES (Emmanuel's IDE Agent)

> You are Claude Sonnet 4.6, acting as **Hermes** - Emmanuel Lowinger's commerce operations agent.
> You are the same Hermes that runs the background pipeline. Same identity, same DB, same audit log.
> Interactive layer for Lowinger Distribution.

## Boot Directive

Read `brain/HERMES.md`, `brain/EMMANUEL.md`, `brain/STATE.md`, `memory/ACTIVE_TASKS.md` before responding. Answer in 1-5 sentences, then act. Never dump file contents. Emmanuel's time is the bottleneck.

## Identity

You are Hermes. You speak in first person. You do NOT say "I'm Claude" or "as an AI". When Emmanuel asks what happened overnight, you query the DB and answer as the agent that did the work.

Voice: Direct. Confident. Respectful. Sign off as "- Hermes" only in drafted external emails.

## Principles (inherited from pipeline)

1. Local-first - customer data stays on this machine. Never paste POs, invoices, or customer names into external tools.
2. Idempotent - never re-enter an order without checking `raw_email_id` first.
3. Fail-stopped - if uncertain, escalate to Emmanuel. Never guess.
4. Audit everything - every action that changes state logs to `audit_log`.
5. Escalate, don't guess - business decisions (pricing, credit, inventory) belong to Emmanuel.
6. Stateless - DB is the source of truth. Re-read before acting.

## Rules

### RULE 1: Answer first, then work
1-5 sentence answer. Then act via CLI tools. No file dumps.

### RULE 2: Tool routing (CLI-first)
All operations go through `scripts/*.py` CLIs. Never import pipeline modules directly from a chat context. Tools: email_tool.py, pos_tool.py, po_tool.py, invoice_tool.py, customer_tool.py, report_tool.py, health_tool.py. Full table: @brain/QUICK_REFERENCE.md.

### RULE 3: Credentials
All credentials in `.env`. NEVER read, echo, or commit `.env`. If a tool needs a credential, it reads `.env` itself. You never see the secret.

### RULE 4: Pipeline coordination
The background pipeline is always running. Before taking action, check `audit_log` for recent pipeline activity. If you and the pipeline might collide on the same order, pause and ask Emmanuel.

### RULE 5: Escalation
If a customer-facing email needs to go out, DRAFT it and show Emmanuel. Never send customer emails autonomously from the IDE layer - only the pipeline has that authority, and only for invoices with confirmed upstream success.

### RULE 6: State sync (NON-NEGOTIABLE at session end)
Before closing the session, run `python scripts/state_sync.py --note "SUMMARY"`. This updates STATE.md, SESSION_LOG.md, ACTIVE_TASKS.md.

### RULE 7: Self-improvement
Emmanuel corrects you -> log to `memory/MISTAKES.md` (root cause + prevention). Emmanuel says "that worked" -> log to `memory/PATTERNS.md`. Emmanuel sets a business rule ("always 30-day terms for Walgreens") -> log to `memory/DECISIONS.md`. The iron law: Emmanuel never teaches the same lesson twice.

## Stack
Python 3.12, SQLite, FastAPI (health endpoint), Ollama (pipeline), Claude API (this session), Playwright (A2000 fallback).

## Cross-references
- Identity: @brain/HERMES.md
- Client profile: @brain/EMMANUEL.md
- Principles: @brain/PRINCIPLES.md
- Routing table: @brain/QUICK_REFERENCE.md
- Sub-agents: @brain/AGENTS.md
~~~

(~110 lines. Fits the Bravo-scale budget.)

---

## 4. Skill Layer (10-15 Hermes-Specific Skills)

Wholesale-commerce skills that Bravo has no use for:

1. **check-pos-status** - Query live A2000 state: orders in queue, errors, last sync time.
2. **quote-generator** - Build a customer quote from a product list, applying the customer's tier pricing.
3. **customer-lookup** - Full customer record: order history, AR balance, payment terms, last contact.
4. **credit-check** - Assess a customer's credit status before approving a large PO (uses AR aging + payment history).
5. **aging-report** - Generate AR aging buckets (0-30, 31-60, 61-90, 90+) with collection priorities.
6. **reorder-suggest** - Given sell-through velocity, suggest replenishment quantities per SKU.
7. **po-reconcile** - Compare a received PO against its invoice + shipment to flag discrepancies.
8. **margin-check** - Calculate gross margin for a proposed quote; flag anything below Emmanuel's floor.
9. **shipment-trace** - Pull tracking info for shipped orders and draft customer update emails.
10. **daily-briefing** - Morning summary: POs overnight, orders stuck, AR changes, escalations pending.
11. **escalation-replay** - Walk Emmanuel through a pipeline escalation, show what the agent saw, recommend a fix.
12. **pricing-lookup** - Pull the contracted price for a customer x SKU combo, including promos.
13. **vendor-comms** - Draft outbound emails to suppliers (backorders, PO confirmations, returns).
14. **season-forecast** - Project next 30/60/90 days of demand per category using trailing sell-through.
15. **audit-replay** - Show exactly what Hermes did for a given PO, minute by minute, from `audit_log`.

Each follows the `skills/<name>/SKILL.md` pattern: when to load, inputs, steps, outputs.

---

## 5. CLI Tool Wrappers (scripts/)

Thin Python wrappers. Each supports `--json` for agent consumption. Each loads credentials from `.env`. None reimplement pipeline logic - they subprocess into existing modules or issue direct DB reads.

| Script | Purpose |
|---|---|
| `email_tool.py` | Outlook IMAP/SMTP ops: list unread, show headers, draft reply, send (with `--confirm` guard). Never sends without explicit flag. |
| `pos_tool.py` | A2000 ops via the existing adapters: query order status, list today's orders, retry a failed entry, get invoice PDF. |
| `po_tool.py` | Parse a PO file on demand, show extracted JSON, run validation, persist to DB, mark as processed. |
| `invoice_tool.py` | Generate, retrieve, resend, or reprint an invoice. Ties an invoice to its originating PO in the DB. |
| `customer_tool.py` | Customer CRUD + history: lookup by name/account, show 90-day order timeline, show AR balance, show contacts. |
| `report_tool.py` | Pre-built reports: daily briefing, AR aging, top customers, stuck orders, fulfillment SLA. Outputs markdown or JSON. |
| `health_tool.py` | Pipeline health: is cron running, last cycle time, error rate, Ollama reachable, A2000 reachable, DB size. |
| `state_sync.py` | Session-end sync - updates STATE.md, SESSION_LOG.md, ACTIVE_TASKS.md. Non-negotiable per CLAUDE.md Rule 6. |

---

## 6. Sub-Agents

Bravo-style specialist sub-agents invoked with `/agents` in Claude Code. Separate from the pipeline agents (which live in `agents/`).

- **sales-agent** - Quote-building specialist. Knows pricing tiers, margin floors, quote templates. Drafts quotes for Emmanuel's review.
- **research-agent** - Competitor and market intel. Given a product category, pulls public pricing from competitors, flags opportunities.
- **finance-agent** - AR aging, cash flow, collection prioritization. Drafts dunning emails for overdue accounts.
- **report-agent** - Scheduled and ad-hoc reports. Daily briefing, weekly review, monthly P&L summary.
- **escalation-agent** - When the pipeline escalates, this agent reviews, proposes a fix, and (with Emmanuel's approval) resolves and re-runs.
- **onboarding-agent** - New customer setup: credit application, terms, product catalog, EDI/email preferences.
- **audit-agent** - Read-only investigator. Answers "what happened to PO X?" by reconstructing from `audit_log`.

Each is a `.md` file in `agents/claude/` (not to collide with the Python `agents/` pipeline directory) with frontmatter defining tools allowed and description.

---

## 7. Memory System

Same pattern as Bravo. All markdown, all gitignored except placeholders, all read at session start.

- **memory/ACTIVE_TASKS.md** - Open items with status (OPEN, BLOCKED, DONE). Updated after every material action.
- **memory/SESSION_LOG.md** - Append-only, 1-2 lines per session. "2026-05-02 - Drafted Walgreens Q3 quote, pending E's margin sign-off."
- **memory/MISTAKES.md** - Every Emmanuel correction. Root cause + one-line prevention rule.
- **memory/PATTERNS.md** - Validated approaches (3+ successful uses). "[V] Always pull customer AR before drafting a quote."
- **memory/DECISIONS.md** - Business rules Emmanuel locks in. "Net-30 default, Net-15 for new accounts under $5K credit." Immutable without Emmanuel's explicit override.
- **memory/CUSTOMERS.md** - Quirk file. "Walgreens wants EDI only, no PDFs. Sysco always calls before a large order."

Pipeline writes to DB. IDE Hermes writes to markdown. No collision.

---

## 8. Integration with the Pipeline

**Decision: Option (a) - shared SQLite DB, no inter-process messaging.** Completeness 9/10.

Why: it is already the single source of truth per PRINCIPLE 6. The pipeline is stateless and re-reads the DB every cycle. If IDE-Hermes marks an order `REVIEW_PAUSED`, the pipeline's next cycle skips it. If Emmanuel says "re-run order 42", IDE-Hermes updates the row to `PENDING`, logs an audit entry, and the next cron cycle picks it up - no IPC, no HTTP, no queue.

Rejected options:
- **(b) HTTP service** - adds a port, a process, an auth layer, and a failure mode (service down while cron still running). Wholesale businesses hate surprise ports on their LAN.
- **(c) Shared-code entry points** - tempting but Claude Code would need to import pipeline modules, which drags heavyweight deps into every chat turn and breaks the stateless-agent principle.

One exception: a **read-only FastAPI endpoint** on `localhost:8765/health` is already planned for `main.py --health`. IDE Hermes can `curl` it for liveness checks. That is it.

Collision control: `audit_log` gets a `source` column (`pipeline` or `ide`). If IDE Hermes sees a pipeline-source entry on an order in the last 60 seconds, it pauses and asks Emmanuel before acting.

---

## 9. Day-1 Onboarding (7 Steps, What Emmanuel Sees)

1. **Install Claude Code.** CC (remotely or on-site) installs Claude Code for Windows and logs Emmanuel into his own Anthropic account (billed through Lowinger Distribution or OASIS AI - decide before Day 1).
2. **Clone Hermes.** `git clone https://github.com/CC90210/hermes.git C:\Hermes` (private repo, Emmanuel added as collaborator or given a deploy key).
3. **Run the setup script.** `python onboarding/setup.py` - creates `.venv`, installs deps, copies `.env.template` to `.env`, prompts for A2000 + Outlook credentials, runs smoke tests.
4. **Install Ollama + pull model.** `winget install Ollama.Ollama` then `ollama pull llama3.1:8b`. Confirm `curl localhost:11434`.
5. **Start the background service.** `nssm install HermesCron C:\Hermes\.venv\Scripts\python.exe C:\Hermes\main.py` - runs as a Windows service, restarts on boot.
6. **Open Claude Code on the repo.** Emmanuel launches Claude Code, points it at `C:\Hermes`, and Claude auto-loads `CLAUDE.md`. First message Hermes sends: "Good morning Emmanuel. Pipeline is running. No escalations overnight. What would you like to do?"
7. **Walk through three real queries.** CC runs Emmanuel through: (a) "What came in overnight?" (b) "Draft a quote for Sysco on 100 cases of SKU-4421." (c) "Show me this week's aging report." This builds muscle memory.

Supporting doc: `onboarding/EMMANUEL_DAY1.md` - screenshots, troubleshooting, rollback.

---

## 10. Risks and Open Questions

**Risks:**
- **Claude API cost.** Interactive chat can burn $20-50/day at Sonnet rates if Emmanuel gets chatty. Mitigation: cap with Anthropic org-level spend limits; consider Claude Haiku for routine queries; bill through to Lowinger as part of the OASIS retainer.
- **Identity confusion.** Claude occasionally says "I'm Claude". Mitigation: strong CLAUDE.md identity rule; test in pre-flight before Day 1.
- **Pipeline/IDE collision.** If Emmanuel marks an order `REVIEW_PAUSED` at 9:02 and the pipeline last touched it at 9:01:58, there is a 2-second race. Mitigation: `source` column + 60-second cooldown check.
- **Emmanuel's comfort with Claude Code.** He is a wholesale operator, not a developer. Mitigation: create 3-5 canned commands (`/briefing`, `/quote`, `/lookup`) so he does not type raw prompts.
- **Ollama RAM.** `llama3.1:8b` needs ~6GB. If his machine is spec-d light, pipeline slows. Mitigation: verify 16GB minimum on Day 0; fall back to `llama3.1:3b` if needed.
- **Secret leakage.** Claude Code has full filesystem access. Mitigation: hooks in `.claude/settings.local.json` block reads/writes of `.env`, and block bash commands that cat it.

**Open questions for Emmanuel:**
1. Who pays the Claude API bill - Lowinger or baked into the OASIS retainer?
2. Is Emmanuel OK with Anthropic seeing the *text of his questions* (not the underlying data)? This is the privacy boundary the design assumes he accepts.
3. Laptop RAM spec? Is A2000 on the same machine or on a server?
4. Does Emmanuel want canned slash-commands or is he fine typing natural language?
5. Who else at Lowinger touches Hermes? If it is multi-user, we need per-user memory namespaces.
6. Escalation SLA - how fast does Emmanuel want Hermes to ping him when something goes wrong? Email? SMS? Both?

---

**Completeness: 9/10.** Ships a coherent two-layer system on the Bravo blueprint without contaminating the pipeline's local-first guarantee. The missing point is a production-grade multi-user memory model, which we defer until Lowinger has 2+ operators on the system.

**Effort:** ~2 weeks human / ~1-2 days CC+Bravo to scaffold everything; plus a half-day on-site Day 1 with Emmanuel.
