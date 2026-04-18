# Hermes — The Commerce Agent

Autonomous PO processing for wholesale distribution: email → A2000 order entry → invoice email, zero manual intervention.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/CC90210/hermes.git
cd hermes

# 2. Copy environment template and fill in credentials
cp .env.example .env
# Edit .env with your Outlook and A2000 credentials

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the system
python main.py

# Health check
python main.py --health
```

---

## Architecture

The Manager Bot orchestrates three specialist agents: the Email Agent monitors an Outlook inbox for incoming POs and parses attachments (PDF, Excel, EDI) into a normalised schema; the POS Adapter submits structured orders to A2000 via REST API, EDI import, or screen automation depending on available access; the Invoice Agent retrieves the generated invoice and delivers it to the buyer via Outlook. All state is stored in a local encrypted SQLite database — no data leaves the machine.

```
Outlook Inbox
     │
     ▼
Email Agent (classify + parse)
     │
     ▼
Manager Bot (orchestrate + error handling)
     │
     ├──▶ POS Adapter (A2000 order entry)
     │         │
     │         ▼
     └──▶ Invoice Agent (retrieve + email)
               │
               ▼
         Buyer Inbox
```

---

## Project Structure

```
hermes/
├── main.py                  # Entry point
├── manager/                 # Orchestration layer
│   └── bot.py
├── agents/                  # Specialist agents
│   ├── email_agent.py
│   ├── parser.py
│   ├── invoice_agent.py
│   └── notifier.py
├── adapters/                # External system connectors
│   ├── a2000_api.py         # REST API (preferred)
│   ├── a2000_edi.py         # EDI 850 import
│   └── a2000_playwright.py  # Screen automation (fallback)
├── db/                      # Local encrypted SQLite
│   └── schema.sql
├── tests/                   # pytest test suite
│   └── ...
├── docs/                    # Client documentation
│   ├── BUILD_PLAN.md
│   ├── CASE_STUDIES.md
│   ├── SECURITY.md
│   ├── TRIAL_TERMS.md
│   └── DISCOVERY_QUESTIONS.md
└── onboarding/
    └── SETUP_GUIDE.md       # Non-technical operator manual
```

---

## Configuration

All configuration lives in `.env`. Never commit this file.

| Variable | Description |
|----------|-------------|
| `OUTLOOK_EMAIL` | Outlook email address |
| `OUTLOOK_CLIENT_ID` | Microsoft 365 OAuth app ID |
| `OUTLOOK_CLIENT_SECRET` | Microsoft 365 OAuth secret |
| `A2000_API_URL` | A2000 REST API base URL (if available) |
| `A2000_API_KEY` | A2000 API key |
| `A2000_USERNAME` | A2000 admin username (screen automation fallback) |
| `A2000_PASSWORD` | A2000 admin password (screen automation fallback) |
| `DB_ENCRYPTION_KEY` | SQLite encryption key |
| `OPERATOR_EMAIL` | Email address for escalation alerts |

---

## Testing

```bash
pytest tests/
```

Mock mode available for A2000 development without a live instance:

```bash
python main.py --mock-a2000
```

---

## Status

**MVP — In Development**
Target production: May 2026

Phases complete: 0 (Discovery)
In progress: Phase 1 (Email Agent)

---

## Built by OASIS AI Solutions

Conaugh McKenna, Founder
conaugh@oasisai.work | oasisai.work

*Autonomous agent systems for operators who move fast.*
