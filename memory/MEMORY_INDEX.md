---
mutability: FREELY-MUTABLE
tags: [hermes, memory, index]
---

# MEMORY INDEX — What Lives in memory/

> One-line entries. Update this file whenever a new memory file is added or removed.

## Active Files

- [Active Tasks](ACTIVE_TASKS.md) — current work in flight, open/blocked/done
- [Session Log](SESSION_LOG.md) — append-only log of what happened each session
- [Mistakes](MISTAKES.md) — root causes and prevention rules from past failures
- [Patterns](PATTERNS.md) — probationary and validated approaches that work
- [Decisions](DECISIONS.md) — business rules Emmanuel has locked in
- [Customers](CUSTOMERS.md) — customer-specific quirks, compliance requirements, preferences
- [Long Term](LONG_TERM.md) — high-confidence persistent facts that survive session resets
- [Proposed Changes](PROPOSED_CHANGES.md) — staged proposals for SEMI-MUTABLE file changes
- [Self Reflections](SELF_REFLECTIONS.md) — structured failure analysis and post-task reflection
- [Memory Index](MEMORY_INDEX.md) — this file

## Runtime Files (generated, not committed)

These files are created by the running pipeline and are gitignored:

- `failure_patterns.jsonl` — structured records of parsing failures (for Ollama prompt tuning)
- `audit_exports/` — CSV/JSON exports of the audit_log for operator review
- `pattern_detections.json` — aggregated failure pattern counts after analysis

## Maintenance

When the session log exceeds 200 lines, archive older entries to `SESSION_LOG_ARCHIVE_YYYY.md`.
When MISTAKES.md exceeds 30 entries, cluster by root cause category and summarize.

## Obsidian Links
- [[brain/INTERACTION_PROTOCOL]] | [[brain/STATE]] | [[memory/LONG_TERM]]
