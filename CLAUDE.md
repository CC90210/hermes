# Hermes — Agent Instructions

> Any AI working in this repo reads this first.

## Project Context

**Client:** Emmanuel Lowinger — wholesale distributor, clients include Walgreens and similar retailers.
**System:** Hermes (Agent Operating System) — automates the full PO loop: Outlook inbox → A2000 order entry → invoice retrieval → invoice email.
**Built by:** OASIS AI Solutions (Conaugh McKenna, conaugh@oasisai.work)
**Status:** MVP in development. Target production: May 2026.

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| LLM (local) | Ollama — local inference only, no cloud AI |
| Database | SQLite + SQLCipher (encrypted at rest) |
| API layer | FastAPI |
| Browser automation | Playwright (A2000 screen fallback) |
| Email | Microsoft Graph API (Outlook 365) or IMAP |
| Testing | pytest |

## Critical Constraint: Local-Only Processing

**ALL data stays on the client's machine. This is non-negotiable.**
- No calls to OpenAI, Anthropic, or any cloud AI API with client data
- Ollama is the only LLM — runs locally on the client's hardware
- SQLite database is encrypted and never transmitted
- The only external calls are to the client's own Outlook account and A2000 instance

If you are tempted to add a cloud AI call for any reason, stop and use Ollama instead.

## Architecture

```
main.py
  └── manager/bot.py          — Orchestrates all agents, handles errors, escalates
        ├── agents/email_agent.py      — Outlook inbox monitoring + classification
        ├── agents/parser.py           — PO extraction from PDF/Excel/EDI/body
        ├── agents/invoice_agent.py    — Invoice retrieval + outbound email
        └── adapters/
              ├── a2000_api.py         — REST API (Tier 1, preferred)
              ├── a2000_edi.py         — EDI 850 (Tier 2)
              └── a2000_playwright.py  — Screen automation (Tier 4, fallback)
```

The Manager Bot is the only component that calls external agents. Agents are stateless — they read from and write to SQLite only. The Manager drives all sequencing.

## A2000 Integration Tiers

Work through these in order. Use the highest available tier.

1. **REST API** — If `A2000_API_URL` and `A2000_API_KEY` are set in `.env`, use `adapters/a2000_api.py`
2. **EDI 850** — If EDI is configured on the A2000 instance, use `adapters/a2000_edi.py`
3. **Direct DB** — Not implemented. Do not add without explicit instruction. High risk.
4. **Playwright** — Fallback. Implemented in `adapters/a2000_playwright.py`. Use `--mock-a2000` in development.

## Development Rules

- **No hardcoded credentials.** Every secret lives in `.env`. Load with `python-dotenv`. Never log credentials.
- **No `any` types in TypeScript** (not applicable here, but if TypeScript is ever added: enforce types strictly)
- **Mock mode always available.** `main.py --mock-a2000` runs the full pipeline without a live A2000. Tests must pass in mock mode.
- **Every agent action gets a log entry.** Format: `YYYY-MM-DD HH:MM:SS | {agent} | {action} | {result}`
- **Escalate rather than guess.** If parser confidence is below threshold, flag for operator review. Do not enter partial or uncertain data into A2000.
- **Idempotency.** If the same PO is received twice, detect the duplicate and skip. Never double-enter an order.

## Entry Point

```bash
python main.py            # Run the system
python main.py --health   # Health check
python main.py --mock-a2000  # Development mode (no live A2000 required)
```

## Testing

```bash
pytest tests/             # Full test suite
pytest tests/test_parser.py  # Parser only (useful during Phase 1)
```

All tests must pass before any commit. Do not skip or comment out failing tests — fix them.

## File Conventions

- `agents/` — One file per agent. No agent imports from another agent. All shared state via `db/`.
- `adapters/` — One file per A2000 integration tier. The Manager selects which adapter to use at runtime.
- `db/` — Schema migrations in `db/migrations/`. Never alter tables directly — always add a migration.
- `logs/` — Rotated daily. Never commit log files. Add `logs/` to `.gitignore`.
- `tests/` — Mirror the source structure: `tests/agents/`, `tests/adapters/`, etc.

## Secrets and `.env`

`.env` is never committed. `.env.example` is committed with all keys and no values. If you add a new env variable:
1. Add it to `.env.example` with a comment explaining what it is
2. Add it to the credentials table in `README.md`
3. Load it with `os.environ.get("KEY")` — never hardcode a fallback value for a secret

## Obsidian Links
- [[brain/APP_REGISTRY]] | [[memory/SESSION_LOG]]
