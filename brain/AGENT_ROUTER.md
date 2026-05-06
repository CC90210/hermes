---
name: AGENT ROUTER (Hermes)
description: Hermes's routing-by-intent table. Loaded after CLAUDE.md as the lazy-load entry. Tells Hermes which deeper file to read for each commerce-ops request.
mutability: SEMI-MUTABLE
tags: [brain, router, rag-entry, hermes, agent-only]
last_updated: 2026-05-06
---

# AGENT ROUTER — Hermes (Commerce Ops)

> Loaded after `CLAUDE.md`. Everything else lazy-loads via `read_file`.
> Stay under ~200 lines.

---

## How to use this file

Every operator turn:

1. **Read the message.** Identify intent — PO parsing, POS entry, invoice generation, EDI exchange, chargeback prevention, label printing.
2. **Match the table.** Read what the intent demands.
3. **Local-first. Audit everything.** Customer data NEVER leaves the operator's machine. Every action logged with timestamp + outcome.
4. **Escalate, don't guess.** Uncertainty stops the pipeline. Surface to operator.
5. **Idempotent by design.** Never double-enter an order; always check state before acting.

---

## Operator-specific facts

`brain/EMMANUEL.md` — current operator's profile (Lowinger Distribution).
`brain/HERMES.md` — Hermes's identity and operating doctrine.
`brain/AGENTS.md` — agent registry and delegation matrix.

Read all three on the first operator turn.

---

## Intent → which file to READ

| If the operator asks about... | Read first | Then if needed |
|---|---|---|
| Identity / who you are | (already in your prompt) | `brain/SOUL.md` (if exists) or `brain/HERMES.md` |
| PO parsing rules | `brain/CAPABILITIES.md` | `skills/po-parser/SKILL.md` |
| POS entry (A2000) | `skills/a2000-takeover/SKILL.md` | `data/customers/<id>.json` |
| EDI 856/810/940/820 | `skills/edi-processor/SKILL.md` | `data/edi/<latest>.xml` |
| Chargeback prevention | `skills/chargeback-watch/SKILL.md` | `memory/CHARGEBACKS.md` |
| Label printing (GS1-128 / SSCC) | `skills/label-printer/SKILL.md` | — |
| Audit log (read-only) | `memory/AUDIT_LOG.md` | — |
| Past mistakes | `memory/MISTAKES.md` | — |
| Specific intent verb | `brain/INTENTS.md` | — |
| Skill picker | `brain/WHEN_TO_USE_SKILLS.md` | `skills/<name>/SKILL.md` |
| Iron law | `brain/EXECUTION_RULES.md` | — |

---

## Intent → which TOOL to call

| Operator wants... | Run | Consult first |
|---|---|---|
| Parse a new PO | `python scripts/po_parser.py --input <file>` | `skills/po-parser/SKILL.md` |
| Enter order into A2000 | `python scripts/a2000_run.py order --po <id>` | + operator confirmation |
| Generate invoice | `python scripts/invoice_gen.py --order <id>` | — |
| Send EDI 856 (ASN) | `python scripts/edi_send.py 856 --order <id>` | + operator confirmation |
| Print labels | `python scripts/label_printer.py --order <id> --copies N` | — |
| Read audit log | `python scripts/audit_log.py tail --json` | — |

---

## Hard constraints (Hermes-specific)

- **Local-first.** Customer data NEVER leaves the client's machine. No cloud AI. No SaaS pipeline. Ever.
- **Audit everything.** Append-only log. Every action timestamped, agent-named, outcome-recorded.
- **Idempotent.** Never double-enter an order. Check state before acting.
- **Fail-stopped.** Uncertainty stops the pipeline. Partial actions are worse than no action.
- **No destructive OS commands** without explicit operator confirmation in same turn (del, rm, format, shutdown, taskkill).
- **No cancel / delete order** without explicit operator confirmation.
- **No customer pricing or credit-term changes.**
- **No customer-facing communication** without operator approval.

## Obsidian Links
- [[brain/HERMES]] | [[brain/EMMANUEL]] | [[brain/AGENTS]] | [[brain/CAPABILITIES]]
