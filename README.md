# Hermes

**The commerce agent that keeps your back office running while you run the business.**

Built by [OASIS AI Solutions](https://oasisai.work). First deployment: Lowinger Distribution — supplying Walgreens and similar retailers.

---

## The problem Hermes solves

If you're a wholesale distributor, your day looks something like this:

- 6:42 AM — A purchase order drops into your inbox. Walgreens. 180 line items across 12 SKUs.
- 7:15 AM — You stop what you were doing, open the PDF, squint, start typing it into A2000 line by line.
- 9:30 AM — One typo on line 47. You catch it. Another one on line 93. You don't. That one becomes a short-ship chargeback six weeks from now.
- 10:00 AM — You need to send the ASN four hours before the DC receives the shipment. You forget. $340 fine.
- 4:00 PM — You should be at the trade show or on the phone with a new buyer. Instead you're reconciling what Walgreens just deducted from last month's payment.

This is the job. It's the opposite of the work that actually grows your business.

**Hermes takes this whole layer off your plate.** He reads the POs. He enters them into A2000. He sends the ASNs. He generates the GS1-128 carton labels. He catches the mismatches before they become chargebacks. He logs everything. He does it in the background, on your machine, while you're asleep or at a trade show or closing a new account.

When you want to know what happened, you ask him. He answers.

---

## How you talk to Hermes

You open Claude Code on your computer — it's an app like VS Code. You see a chat box. **You type.** Nothing fancier than that.

Like texting a sharp new hire:

```
You:     Hey Hermes, what POs came in overnight?
Hermes:  3 new POs — 2 from Walgreens DC (totals $12,840), 1 from CVS ($3,210).
         All three entered into A2000 clean. ASNs queued for 10:30 AM transmission.
         One flag: CVS PO references SKU LWG-9900 which isn't in your contract
         pricing table. I paused it for your review.
```

**No microphone. No voice AI. No new hardware.** Just your keyboard and Claude Code. If you already use Cursor, VS Code, or any modern editor, this will feel familiar.

There are shortcuts too — slash commands for the things you'll ask a hundred times:

| What you type | What happens |
|---|---|
| `/status` | Current order counts, failures, system health |
| `/daily-briefing` | 5-bullet morning summary |
| `/chargebacks` | Every open chargeback with its dispute deadline |
| `/quote Walgreens` | Interactive quote builder for that customer |
| `/customer CVS` | Full customer profile — credit, AR, order history, red flags |

Full set in `docs/EMMANUEL_GUIDE.md`.

---

## What's under the hood

Hermes is two things running together, sharing the same brain:

**The background pipeline** — a Python service that runs on a cron schedule every 5 minutes. It watches your inbox, parses incoming POs (PDF, Excel, EDI X12, or plain text) using a local AI model called Ollama that runs on your machine, enters orders into A2000, retrieves invoices, and emails them back to your customers. You don't talk to this one. It just works.

**The interactive agent** — Hermes in Claude Code. When you open the IDE, he loads his identity (`brain/HERMES.md`), remembers your past conversations (`memory/`), and waits for you. You type, he acts, he reports back. Same database as the pipeline, so what you see is what the pipeline just did.

```
Your Outlook Inbox
     ↓
Email Agent  ──────▶  PO Parser (local Ollama LLM)
                              ↓
                      Manager Bot (orchestrate, retry, escalate)
                              ↓
    ┌─────────────────────────┼─────────────────────────┐
    ▼                         ▼                         ▼
POS Adapter              EDI 855 Ack              GS1-128 Labels
(A2000: API, EDI,        (within 24-48h)          + EDI 856 ASN
 or screen automation)                            (pre-ship, compliance)
    │
    ▼
Invoice Agent  ──────▶  Your Customer's Inbox
    │
    ▼
EDI 820 Parser  ──────▶  Chargeback Tracker (4-week dispute window)
```

Everything lives on your machine. No cloud AI touches your customer data. Your emails, your orders, your pricing — they never leave your network.

---

## What Hermes can reach on your computer

Hermes isn't sandboxed inside a browser or a chat window. He runs as a real Windows application with the keys to the machine:

- **Printing.** He prints warehouse POs to whatever printer you assign (`python scripts/printer_tool.py --list` shows every printer Windows sees). He sends raw ZPL to your Zebra thermal printer for Walgreens-compliant GS1-128 carton labels. He prints invoices as paper backups on request.
- **Folder watching.** If IMAP is blocked on your network, Hermes watches a folder on your machine — drop a PO PDF in and he processes it the same way he would an email.
- **Desktop notifications.** Toast popups the moment something needs your attention. No more missing a failure because you weren't checking email.
- **File and app handling.** Opens files, copies to clipboard, takes screenshots for escalation attachments.

All of this is gated by a strict safety layer: no arbitrary shell commands, no destructive OS calls, path traversal blocked, every action audit-logged, credentials sanitized out of anything Hermes touches.

---

## What's real today (evidence)

This isn't a pitch deck. This is a working system:

- **215 automated tests** currently pass. Every change gets verified.
- **End-to-end demo runs in 0.10 seconds** on mock data — parses a PO, enters the order, retrieves the invoice, drafts the customer email. Deterministic across 20 consecutive runs. You can run it yourself right now (`python -m demo.run_demo`).
- **Deeply audited.** Four independent review passes (code quality, runtime stress, security, architecture) — every P0 and P1 finding fixed before ship.
- **Ruff-clean.** Zero lint errors across the production codebase.
- **38 discovery questions** already drafted for client onboarding (`docs/DISCOVERY_QUESTIONS.md`).
- **13 CLI tools** Hermes can call — report, quote, customer lookup, chargeback tracker, invoice resend, printer control, system ops, and more.
- **9 slash commands** wired up in Claude Code (`/status`, `/daily-briefing`, `/chargebacks`, `/quote`, `/customer`, `/draft-email`, `/print`, `/re-run-order`, `/process-pending`).

The demo output looks like this:

```
📧 PO received   (sample_po.txt, 694 chars)            [0.00s]
🤖 PO parsed     (PO# PO-2026-04567, 3 line items)     [0.10s]
📦 Order entered into A2000  (order_id=MOCK-069E55CA)  [0.00s]
🧾 Invoice retrieved          (81 bytes, INV-3EED09)   [0.00s]
✉️  Invoice would be emailed  (purchasing@walgreens.com)

All 5 pipeline steps completed successfully.
Runtime: 0.11s
```

---

## For client meetings — the demo package

Open **[`docs/DEMO.html`](docs/DEMO.html)** in a browser for the self-contained client-facing visual (dark theme, 10 sections, works offline, prints clean to PDF). Back it up with `python -m demo.run_demo` in a terminal for the live ~0.1s pipeline proof. Full walkthrough script and agenda live in [`docs/MEETING_PLAN.md`](docs/MEETING_PLAN.md). Architecture diagrams for markdown viewers are in [`docs/DEMO.md`](docs/DEMO.md).

---

## Installation

One command on Windows:

```powershell
git clone https://github.com/CC90210/hermes.git
cd hermes
powershell -ExecutionPolicy Bypass -File install.ps1
```

One command on macOS / Linux:

```bash
git clone https://github.com/CC90210/hermes.git
cd hermes
bash install.sh
```

The installer checks Python, creates a virtual environment, installs dependencies, pulls the local AI model, initializes the database, and runs the demo to verify everything works. When it's done, you open the folder in Claude Code and start talking to Hermes.

Prefer the long way? See `docs/SETUP_GUIDE.md` for the plain-English operator manual.

---

## Configuration

Credentials and settings live locally and are never committed to git. Hermes reads `.env.agents` first when the OASIS setup wizard creates it, then `.env` for any remaining deployment settings. Direct installs copy `.env.template` to `.env`; open it in a text editor and fill in the real values.

The variables are organized in four groups:

**The local AI model** — where Ollama runs on your machine.
- `OLLAMA_HOST`, `OLLAMA_MODEL`

**Your email** — how Hermes reads incoming POs and sends invoices back.
- `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_IMAP_PORT`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`

**Your POS system (A2000)** — how Hermes talks to your order system. Pick the mode that matches your setup (`mock` is safe for the trial).
- `A2000_MODE` (one of: `mock`, `api`, `edi`, `playwright`)
- `A2000_API_URL`, `A2000_API_KEY` (for `api` mode)
- `EDI_OUTPUT_DIR`, `EDI_SENDER_ID`, `EDI_RECEIVER_ID` (for `edi` mode)

**Your business** — identity used on invoices and escalation alerts.
- `COMPANY_NAME`, `ESCALATION_EMAIL`, `LOG_LEVEL`

Every variable is documented inline in `.env.template`. Nothing is hidden. Nothing phones home.

---

## Security (why your data stays yours)

Hermes was built for operators who ship sensitive data to sensitive retailers. Every design choice reflects that:

- **Local-first AI by default.** The model that reads your POs runs on your hardware via [Ollama](https://ollama.com). Cloud parsing is optional and should only be enabled with explicit client approval, the right data terms, and `HERMES_PO_PARSER` set intentionally.
- **Encrypted SQLite.** All order data, audit logs, and customer info stored locally with at-rest encryption.
- **Credentials isolated.** Never in code, never in logs, never in version control — only in `.env`, which is gitignored by default.
- **Full audit trail.** Every single action Hermes takes gets logged with timestamp and reason. You can replay any decision he made, any time.
- **Fail-stopped, not fail-open.** When Hermes is unsure, he pauses and alerts you. He never guesses on your behalf.
- **Escalation, not automation creep.** Hermes drafts dispute emails but doesn't send them. Drafts quotes but doesn't price them outside your contract table. You stay in control of everything that touches a customer.

Deeper security posture: `docs/SECURITY.md`.

---

## Project layout

The folder structure reflects how Hermes thinks about himself:

```
hermes/
├── CLAUDE.md                 ← The first file Hermes reads when you open the IDE
├── brain/                    ← Who Hermes is (identity, principles, capabilities)
├── skills/                   ← How Hermes does specific jobs (po-parsing, labels, etc.)
├── clients/                  ← Per-deployment config (Lowinger is the first)
├── .claude/commands/         ← Slash commands like /status and /daily-briefing
├── agents/                   ← The pipeline agents (email, POS, phone)
├── adapters/                 ← Integrations (A2000, EDI formats, labels, pricing)
├── manager/                  ← The orchestrator that ties it all together
├── storage/                  ← SQLite + audit log
├── scripts/                  ← 11 CLI tools Hermes can call
├── demo/                     ← Mock-mode end-to-end demo
├── tests/                    ← 141 automated tests
├── docs/                     ← Everything humans need to read
└── memory/                   ← Runtime state (gitignored; per-deployment)
```

---

## Status

**Version 0.2.0 — demo-ready, fully audited.** The core pipeline (email → parse → POS → invoice) is production-grade and tested. The compliance layer (EDI 855, 856, 820, GS1-128 labels, contract pricing, credit checks, chargeback dispute tracking) has real implementations — tests pass, demos run — waiting on client discovery answers to configure for real data. The OS layer (real printer control, folder watching, desktop notifications, clipboard, screenshots) is live and security-hardened.

**Target Walgreens-ready production: 6–8 weeks from discovery kickoff.**

---

## A note on what this really is

Hermes isn't automation. Automation is what you do when you want to be replaced. Hermes is what you do when you want your best hours back. The back-office isn't going to win you customers. Relationships, trade shows, and conversations win customers. Hermes takes the unglamorous, high-liability, high-repetition work off your hands so you can be somewhere that matters.

He's a team member. Talk to him like one. Trust him with the routine. Own the rest.

---

Conaugh McKenna · [conaugh@oasisai.work](mailto:conaugh@oasisai.work) · [oasisai.work](https://oasisai.work)

*Autonomous agent systems for operators who move fast.*
