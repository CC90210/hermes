---
mutability: FREELY-MUTABLE
tags: [hermes, brain, changelog, audit]
---

# CHANGELOG — Self-Modification Audit Trail

> Separate from git log. Tracks when Hermes's OWN rules and identity changed.
> Code changes go in git. Governance changes go here.
> Append only — never edit existing entries.

## Format
```
## YYYY-MM-DD — [title]
**Files changed:** [list]
**Mutability tier:** SEMI-MUTABLE | GOVERNED | etc.
**What changed:** Brief description
**Why:** Reason for the change
**Review date:** 30 days from entry (for SEMI-MUTABLE changes)
```

---

## 2026-04-18 — v0.1.0 — Initial build
**Files changed:** CLAUDE.md, brain/HERMES.md, brain/PRINCIPLES.md, brain/ARCHITECTURE.md,
brain/CAPABILITIES.md, brain/AGENTS.md, brain/EMMANUEL.md, brain/QUICK_REFERENCE.md, brain/STATE.md,
memory/README.md, 8 CLI scripts, install.ps1
**Mutability tier:** N/A (initial creation)
**What changed:** Complete Hermes commerce agent scaffolded. IDE interaction layer, CLI tools,
brain files, slash commands, and test suite (36 tests passing).
**Why:** First deployment for Emmanuel Lowinger, Lowinger Distribution.
**Review date:** N/A

---

## 2026-04-18 — v0.2.0 — Growth layer installed
**Files changed:** brain/SOUL.md (new), brain/BRAIN_LOOP.md (new), brain/GROWTH.md (new),
brain/INTERACTION_PROTOCOL.md (new), brain/HEARTBEAT.md (new), brain/CHANGELOG.md (new),
memory/LONG_TERM.md (new), memory/PROPOSED_CHANGES.md (new), memory/SELF_REFLECTIONS.md (new),
memory/MEMORY_INDEX.md (new), memory/ACTIVE_TASKS.md (seeded), memory/SESSION_LOG.md (seeded),
memory/MISTAKES.md (seeded), memory/PATTERNS.md (seeded), memory/DECISIONS.md (seeded),
memory/CUSTOMERS.md (seeded), CLAUDE.md (updated boot sequence), memory/README.md (expanded)
**Mutability tier:** SEMI-MUTABLE (approved by CC during architecture session)
**What changed:** Added full self-evolution governance layer. Hermes now has explicit reasoning
protocol (BRAIN_LOOP), skill growth lifecycle (GROWTH), session governance (INTERACTION_PROTOCOL),
proactive health monitoring (HEARTBEAT), identity declaration (SOUL), and populated memory files
with real starter content from the build process.
**Why:** Hermes needs to grow over time as Emmanuel's business scales. Without governance, capability
additions are ad-hoc and untracked. With this layer, every new skill is proven before trusted.
**Review date:** 2026-05-18

---

## Obsidian Links
- [[brain/INTERACTION_PROTOCOL]] | [[brain/GROWTH]] | [[memory/PROPOSED_CHANGES]]
