# Hermes — AI Coding Instructions

> You are working in the Hermes codebase.
> Hermes is OASIS AI's wholesale commerce agent product.

## Purpose

Hermes automates the full purchase-order lifecycle for wholesale distributors:
inbox monitoring → PO parsing → A2000 order entry → invoice retrieval → invoice delivery.
Each client runs their own isolated deployment. No cloud AI. No shared data.

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| LLM | Ollama only — local inference, never cloud |
| Database | SQLite (`aiosqlite`) |
| API layer | FastAPI |
| Email | IMAP + SMTP (or Microsoft Graph API) |
| Browser automation | Playwright (A2000 fallback only) |
| Testing | pytest, 36 tests |

## Architecture (one paragraph)

`main.py` delegates to `cron/scheduler.py` for CLI parsing. The Orchestrator
(`manager/orchestrator.py`) owns the pipeline and holds references to EmailAgent,
POParser, POSAgent, and the active A2000 adapter. Agents are stateless — they read
and write only through `storage/db.py`. The A2000 adapter is selected at runtime via
`A2000_MODE` env var; all four adapters implement `A2000ClientBase`. See
`brain/ARCHITECTURE.md` for the full diagram.

## Rules

1. **Read `brain/PRINCIPLES.md` before non-trivial changes.** The six principles
   (local-first, idempotent, fail-stopped, audit everything, escalate don't guess,
   stateless agents) govern every design decision.

2. **Never commit `.env`.** Credentials live only on the client's machine.
   Add new env vars to `.env.template` and `clients/<name>/.env.client.template`.

3. **Never break `A2000ClientBase`.** All four adapters must remain substitutable.
   Do not add required arguments to abstract methods or change return types.

4. **Tests must stay green.** Run: `.venv/Scripts/python.exe -m pytest tests/`
   All 36 tests must pass before any commit.

5. **Every agent action logs to audit_log.** Call `storage.db.log_audit()` with
   agent_name, action, and a details dict. The audit log is append-only.

6. **No cloud AI calls.** All LLM inference goes to Ollama. If you are tempted to
   call OpenAI or Anthropic with client data, stop and use Ollama instead.

## Entry Points

```bash
python main.py                    # Run forever (300s cycle interval)
python main.py --once             # Single cycle then exit
python main.py --health           # Print health JSON and exit
python main.py --interval N       # Run forever with N-second interval
python main.py --mock-a2000       # Force A2000_MODE=mock for this run

demo/run_demo.py                  # Full pipeline demo with mock data
demo/demo_with_ollama.py          # Demo with real local LLM
```

## Testing

```bash
.venv/Scripts/python.exe -m pytest tests/              # Full suite
.venv/Scripts/python.exe -m pytest tests/test_parser.py  # Parser only
```

## File Conventions

- `agents/` — One class per agent. Agents do not import each other.
- `adapters/` — One file per A2000 tier + `po_parser.py` (parser adapter).
- `storage/` — Schema in `db.py`. Migrations in `db/migrations/`. Never alter tables directly.
- `tests/` — Mirror source structure. Add fixtures to `tests/fixtures/`.
- `brain/` — Identity, architecture, capabilities, agents, principles. Read before coding.
- `skills/` — Domain-specific playbooks. Read the relevant SKILL.md before touching that domain.
- `clients/` — Per-client config overlays. No real credentials ever.
- `memory/` — Runtime state only. Gitignored except `.gitkeep` and `README.md`.

## Cross-References

- Identity and purpose: @brain/HERMES.md
- Technical architecture: @brain/ARCHITECTURE.md
- Sub-agent registry: @brain/AGENTS.md
- Capability registry: @brain/CAPABILITIES.md
- Operating principles: @brain/PRINCIPLES.md
