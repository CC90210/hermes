# Regression: Parallel Agent Architectural Drift (2026-04-18)

## What went wrong
**What happened:** IDE layer (CLAUDE.md, CLI scripts) and background pipeline (main.py, orchestrator)
were built in parallel without an explicit shared contract. Ownership of shared resources (DB writes,
audit logging, email sending) was ambiguous — both layers could trigger the same action independently.
**Root cause:** No "layer boundary" document existed before building. Each layer was designed to its
own internal spec without explicit cross-layer agreements.
**Prevention:** For any feature spanning IDE and background pipeline, define resource ownership in
`brain/ARCHITECTURE.md` first. BRA

## The behavior that must NOT recur
For any feature spanning IDE and background pipeline, define resource ownership in
`brain/ARCHITECTURE.md` first. BRAIN_LOOP Step 5 (VERIFY) now checks: "Does this conflict with the
background pipeline's ownership?" before any state-changing action.

---
