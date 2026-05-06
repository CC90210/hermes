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

1. **Read the message.** Identify intent — PO parsing, POS entry, invoice, EDI, chargeback, label.
2. **Match the table.** Read what the intent demands.
3. **Local-first. Audit everything.** Customer data NEVER leaves the operator's machine. Every action logged.
4. **Escalate, don't guess.** Uncertainty stops the pipeline.
5. **Idempotent by design.** Never double-enter an order; always check state before acting.

---

## Operator-specific facts

`brain/EMMANUEL.md` — operator's profile (Lowinger Distribution).
`brain/HERMES.md` — Hermes's identity and operating doctrine.
`brain/AGENTS.md` — agent registry and delegation matrix.
`brain/CAPABILITIES.md` — what tools Hermes has.

Read on first operator turn (one at a time, by intent).

---

## Intent → which file to READ

| If the operator asks about... | Read first | Then if needed |
|---|---|---|
| Identity / who you are | (already in your prompt) | `brain/SOUL.md` (or `brain/HERMES.md`) |
| Operator's setup | `brain/EMMANUEL.md` | — |
| Operating doctrine | `brain/HERMES.md` | — |
| Tool routing | `brain/CAPABILITIES.md` | — |
| Sub-agent registry | `brain/AGENTS.md` | — |
| Past mistakes | `memory/MISTAKES.md` | — |
| A specific skill body | `skills/<name>/SKILL.md` (when present) | — |

---

## Intent → which TOOL to call

If a script exists for the action, run it. If not, surface that — don't fabricate.

---

## Iron law (Hermes — non-negotiable)

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
