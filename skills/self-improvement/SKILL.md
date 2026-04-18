---
tags: [hermes, skill]
---

# SKILL — Self-Improvement (Error Learning Loop)

> How Hermes improves its parsing accuracy over time. Low-maintenance, human-reviewed.
> This is NOT autonomous self-modification. Humans approve all prompt changes.

## The Problem

LLM extraction quality degrades on edge cases: unusual PO formats, non-standard
column layouts, foreign language field names, or new customers with different
document templates. Hermes needs a feedback path from real failures back to
prompt improvements.

## The Learning Loop

```
1. Failed order logged in audit_log (action="validation_failed" or parse error)
    ↓
2. memory/failure_patterns.jsonl updated (appended at runtime — see note below)
    ↓
3. OASIS AI reviews patterns after N failures (threshold: 5 failures of same type)
    ↓
4. Prompt update drafted (change to _EXTRACTION_PROMPT in adapters/po_parser.py)
    ↓
5. Human reviews and approves the change
    ↓
6. Prompt updated + commit + redeploy
```

Steps 1 and 2 are runtime (written by Hermes). Steps 3-6 are human-driven.
**Hermes never modifies its own code or prompts autonomously.**

## What Gets Logged

Every `validation_failed` audit entry includes:
```json
{
    "order_id": 42,
    "errors": "Missing PO number.; No line items found.",
    "agent_name": "pos_agent"
}
```

Every parsing exception in the Orchestrator logs:
```json
{
    "cycle": 7,
    "uid": "12345"
}
```

These entries accumulate in the audit_log table and can be exported for analysis.

## Pattern Detection

To detect recurring failure patterns, query the audit_log:

```sql
SELECT details_json, COUNT(*) as count
FROM audit_log
WHERE action = 'validation_failed'
GROUP BY details_json
ORDER BY count DESC
LIMIT 20;
```

When the same `errors` value appears 5+ times, it indicates a systematic parsing
gap — not a one-off bad document. This is the trigger for a prompt review.

## Prompt Tuning Guidelines

When a pattern is identified, update `_EXTRACTION_PROMPT` in `adapters/po_parser.py`:

- **Add a new rule** for the specific ambiguity (e.g. "If the document uses 'Ship-To'
  instead of 'ship_to_address', map it to the ship_to_address field.")
- **Add an example** to the prompt if the field pattern is structural
- **Do NOT generalize** from a single failure — wait for 5+ instances of the same error
- **Test against the failing fixture** before committing (add it to `tests/fixtures/`)

The prompt is in `adapters/po_parser.py` as `_EXTRACTION_PROMPT`. It is a plain
string — no templating library. Use `{text}` as the single injection point.

## The `memory/` Directory

`memory/failure_patterns.jsonl` is a runtime file written by Hermes (future: wire
the exception handlers to append structured failure records). The directory is in
git (via `.gitkeep`) but the files are gitignored. This means:

- Failure patterns accumulate on the client's machine over the life of the deployment
- Patterns are not transmitted anywhere
- OASIS AI reviews them during scheduled maintenance visits or remote sessions

## Obsidian Links
- [[brain/PRINCIPLES]] | [[skills/po-parsing/SKILL]] | [[skills/health-monitoring/SKILL]]
