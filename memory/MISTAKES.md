---
mutability: GOVERNED
tags: [hermes, memory, mistakes, prevention]
---

# Hermes — Mistakes Log

> Every time Hermes fails or Emmanuel corrects it: log root cause + one-line prevention.
> The iron law: Emmanuel never teaches the same lesson twice.

---

### Parallel Agent Architectural Drift (2026-04-18)
**What happened:** IDE layer (CLAUDE.md, CLI scripts) and background pipeline (main.py, orchestrator)
were built in parallel without an explicit shared contract. Ownership of shared resources (DB writes,
audit logging, email sending) was ambiguous — both layers could trigger the same action independently.
**Root cause:** No "layer boundary" document existed before building. Each layer was designed to its
own internal spec without explicit cross-layer agreements.
**Prevention:** For any feature spanning IDE and background pipeline, define resource ownership in
`brain/ARCHITECTURE.md` first. BRAIN_LOOP Step 5 (VERIFY) now checks: "Does this conflict with the
background pipeline's ownership?" before any state-changing action.

---

### Aspirational Capability Description in README (2026-04-18)
**What happened:** Early README described "voice interaction" as a Hermes capability, but no voice
code existed. This created false expectations with no implementation behind them.
**Root cause:** README was written aspirationally rather than against the actual codebase. No
distinction was made between "live now" and "planned for Phase N."
**Prevention:** All capability claims in README, CAPABILITIES.md, and brain files must match
current code. Forward-looking items are explicitly labeled "Phase N (not yet implemented)."
No capability is described without a corresponding test or code path. Always run
`python -m pytest tests/ -q` after writing any capability claim to verify the code exists.

---

*New mistakes appended as they occur. Cluster by root cause category quarterly.*

## Root Cause Categories (for quarterly review)

- `boundary` — unclear ownership between systems or layers
- `validation` — missing input validation before acting
- `external-drift` — external system (A2000, email server) behaved unexpectedly
- `spec-ambiguity` — requirement was unclear or underdefined
- `idempotency` — action was repeated when it should have been skipped

## Obsidian Links
- [[brain/BRAIN_LOOP]] | [[memory/PATTERNS]] | [[memory/SELF_REFLECTIONS]]
