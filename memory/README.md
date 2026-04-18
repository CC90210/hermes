---
tags: [hermes, brain]
---

# memory/ — Runtime State Directory

> This directory is in git. Its CONTENTS are not.

## Purpose

Hermes writes runtime state here during operation. These files are per-deployment,
never shared, and never committed. Examples:

- `failure_patterns.jsonl` — structured records of parsing failures (for prompt tuning)
- `audit_exports/` — CSV/JSON exports of the audit_log for operator review
- `pattern_detections.json` — aggregated failure pattern counts after analysis

## What Is and Is Not Committed

```
memory/
├── .gitkeep     ← committed (keeps the directory in git)
├── README.md    ← committed (this file)
└── *            ← NOT committed (all runtime files are gitignored)
```

The `.gitignore` pattern that enforces this:
```
# Runtime state (per-deployment, never committed)
memory/*
!memory/.gitkeep
!memory/README.md
```

## Notes for OASIS AI

When doing a maintenance visit or remote session:
- Query `memory/failure_patterns.jsonl` for recurring parse errors
- Check `memory/audit_exports/` for any operator-requested exports
- Never commit anything from this directory back to the product repo

## Obsidian Links
- [[brain/PRINCIPLES]] | [[skills/self-improvement/SKILL]]
