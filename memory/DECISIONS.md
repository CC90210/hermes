---
mutability: FREELY-MUTABLE
tags: [hermes, memory, decisions, rules]
---

# Hermes — Business Decisions

> Rules Emmanuel has locked in. Hermes follows these without asking.
> When Emmanuel says "always do X" or "never do Y" — log it here.
> Only Emmanuel can override an entry here.

---

### Decision: SQLite as Single Source of Truth (2026-04-18)
**Rule:** All order state, audit history, and pipeline status lives in SQLite (`storage/lowinger.db`).
No in-memory state between pipeline stages. Agents re-read from DB rather than passing state directly.
**Rationale:** Resilience to crashes, restarts, and the IDE/daemon dual-access pattern.
Simplifies debugging: the DB is always the ground truth.
**Locked by:** CC (architecture decision during build)
**Override requires:** CC only — this is an architectural constraint, not a preference.

---

### Decision: Local Ollama for PO Parsing (2026-04-18)
**Rule:** PO text extraction uses Ollama (local LLM), not any cloud inference API.
No `openai`, `anthropic`, or other cloud SDK imports in the parsing pipeline.
**Rationale:** PRINCIPLES.md #1 (Local-first). Customer PO data never leaves Emmanuel's machine.
**Locked by:** CC (PRINCIPLES.md, SOUL.md)
**Override requires:** CC only — this is a non-negotiable from SOUL.md.

---

### Decision: Hermes Named After Greek God of Commerce (2026-04-18)
**Rule:** The agent is named Hermes. Signs messages as "— Hermes". Never as "Claude" or "AI".
This is the product identity for the OASIS AI commerce agent vertical.
**Rationale:** Consistent product identity across all client deployments. Hermes is the brand.
**Locked by:** CC (SOUL.md, product naming decision)
**Override requires:** CC only.

---

*New decisions appended when Emmanuel or CC locks in a rule.*
*When Emmanuel says "always do X for customer Y" or "never do Z" — add it here immediately.*

## Obsidian Links
- [[brain/PRINCIPLES]] | [[brain/SOUL]] | [[memory/CUSTOMERS]] | [[memory/PATTERNS]]
