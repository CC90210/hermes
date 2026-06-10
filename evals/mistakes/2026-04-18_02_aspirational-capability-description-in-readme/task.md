# Regression: Aspirational Capability Description in README (2026-04-18)

## What went wrong
**What happened:** Early README described "voice interaction" as a Hermes capability, but no voice
code existed. This created false expectations with no implementation behind them.
**Root cause:** README was written aspirationally rather than against the actual codebase. No
distinction was made between "live now" and "planned for Phase N."
**Prevention:** All capability claims in README, CAPABILITIES.md, and brain files must match
current code. Forward-looking items are explicitly labeled "Phase N (not yet implemented)."
No capability is described without a corresponding test or code path. Alw

## The behavior that must NOT recur
All capability claims in README, CAPABILITIES.md, and brain files must match
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
- `idempotency` — action was repeated when it should have been ski
