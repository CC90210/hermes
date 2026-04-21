# Hermes — The Commerce Agent

Autonomous PO processing for wholesale distribution: email → A2000 order entry → invoice email, with Walgreens-grade EDI compliance (855/856/810/820) and GS1-128 carton labels. All local, no data egress.

Built by [OASIS AI Solutions](https://oasisai.work). First deployment: Lowinger Distribution.

---

## Why "Hermes"?

Greek god of commerce, merchants, and messengers. He moved between worlds carrying messages and facilitating trade between buyers and sellers. Your commerce agent does exactly this: moves between your email inbox and your POS system, carrying purchase orders in and invoices back out.

**Pronunciation:** HER-meez · **First line to speak aloud:** "Hey Hermes, what's the status?"

---

## Quick Start

```powershell
# Windows one-shot installer
git clone https://github.com/CC90210/hermes.git
cd hermes
powershell -ExecutionPolicy Bypass -File install.ps1
```

Then open the folder in Claude Code. Type `/daily-briefing`. That's it.

Manual install:
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env           # fill in credentials
python scripts/setup_db.py      # initialize SQLite
python -m demo.run_demo         # verify (mock mode, no creds needed)
python main.py                  # production loop
```

---

## Architecture

```
Outlook Inbox
     │
     ▼
Email Agent (poll, classify, parse PO via local Ollama LLM)
     │
     ▼
Manager Bot (orchestrate, retry, escalate)
     │
     ├──▶ POS Adapter (A2000: mock | REST API | EDI 850 | Playwright)
     │         │
     │         ├──▶ EDI 855 PO Ack (within 24-48hr)
     │         ├──▶ EDI 856 ASN + GS1-128 carton labels (pre-ship)
     │         └──▶ Invoice retrieval
     │
     ├──▶ Invoice Agent (SMTP back to buyer)
     │
     └──▶ Remittance Agent (EDI 820 parse, chargeback dispute tracking)
```

All state in local encrypted SQLite. Ollama runs local. No cloud AI touches customer data.

---

## Project Structure

```
hermes/
├── CLAUDE.md                 Agent entry point (Hermes identity + rules)
├── AGENTS.md                 External AI tool pointer
├── main.py                   Background pipeline entry
├── install.ps1               Windows installer
├── .claude/
│   └── commands/             Slash commands (/status, /daily-briefing, etc.)
├── brain/                    Hermes self-understanding
│   ├── HERMES.md            Identity
│   ├── PRINCIPLES.md        Operational principles
│   ├── ARCHITECTURE.md      System architecture
│   ├── CAPABILITIES.md      What Hermes can do
│   ├── AGENTS.md            Sub-agent registry
│   ├── EMMANUEL.md          Client profile
│   ├── STATE.md             Ephemeral operational state
│   └── QUICK_REFERENCE.md   Intent → CLI routing
├── skills/                   Playbooks (po-parsing, a2000-integration, etc.)
├── clients/                  Per-deployment config overlays
│   └── lowinger/            Emmanuel's deployment
├── agents/                   Pipeline agents
│   ├── email_agent.py
│   ├── pos_agent.py
│   └── phone_agent.py       (Phase 2)
├── adapters/                 Integrations
│   ├── po_parser.py         LLM-based PO extraction
│   ├── a2000_client.py      4-mode A2000 adapter
│   ├── edi_855_ack.py       PO acknowledgment
│   ├── edi_856_asn.py       Advance Ship Notice
│   ├── edi_820_remit.py     Remittance parser
│   ├── gs1_128_label.py     Carton labels (ZPL + PDF)
│   ├── matrix_expander.py   Apparel size-color matrix
│   ├── contract_price.py    Customer pricing lookup
│   ├── credit_check.py      Credit hold workflow
│   ├── chargeback_tracker.py 4-week dispute tracking
│   └── invoice_generator.py
├── manager/                  Orchestration
│   ├── orchestrator.py
│   └── config.py
├── storage/                  SQLite + audit log
├── cron/                     Scheduler
├── scripts/                  11 CLI tools (report, po, pos, email, invoice,
│                             customer, quote, chargeback, health, state_sync,
│                             setup_db) — all Hermes-callable
├── demo/                     Mock-mode end-to-end demo
├── tests/                    141 pytest tests
├── memory/                   Runtime state (gitignored contents)
└── docs/                     Documentation
    ├── EMMANUEL_GUIDE.md     Client cheat sheet
    ├── SETUP_GUIDE.md        Non-technical operator manual
    ├── DISCOVERY_QUESTIONS.md 38-question intake
    ├── BUILD_PLAN.md         Phase-by-phase roadmap
    ├── MEETING_PLAN.md       Demo playbook
    ├── WHOLESALE_RESEARCH.md  Industry research
    ├── ARCHITECTURE.md
    ├── DEPLOYMENT.md
    ├── SECURITY.md
    ├── TRIAL_TERMS.md
    ├── CASE_STUDIES.md
    └── IDE_HERMES_DESIGN.md
```

---

## Configuration

Credentials live in `.env` (never committed). Client-specific overlays in `clients/<name>/.env.client.template`.

Core variables: `OLLAMA_HOST`, `OLLAMA_MODEL`, `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_PASSWORD`, `A2000_MODE` (mock | api | edi | playwright), `A2000_API_URL`, `A2000_API_KEY`, `COMPANY_NAME`, `ESCALATION_EMAIL`, `LOG_LEVEL`. Full list in `.env.template`.

---

## Testing

```bash
.venv\Scripts\python.exe -m pytest tests/ -q
```

Current: **141 passed, 1 skipped, 0 failed.** Demo runs end-to-end in mock mode in ~0.11s.

---

## Status

**v0.1.0 — demo-ready.** Phases 1-3 (email ingestion, PO parsing, POS mock entry, invoice loop) live. Phases 2b-7b (ASN/labels/855/820/pricing/credit/chargeback) scaffolded and tested; wire-up pending client discovery answers.

Target Walgreens-ready: 6-8 weeks post-discovery.

---

Conaugh McKenna · conaugh@oasisai.work · [oasisai.work](https://oasisai.work)

*Autonomous agent systems for operators who move fast.*
