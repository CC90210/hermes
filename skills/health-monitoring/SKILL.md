---
tags: [hermes, skill]
---

# SKILL — Health Monitoring

> How Hermes reports its own health and escalates when something is wrong.

## The `/health` Check

`Orchestrator.health_check()` returns a dict with six fields:

```python
{
    "email_connected": bool,    # EmailAgent._imap is not None
    "a2000_reachable": bool,    # A2000Client.is_reachable() returned True
    "pending_orders": int,       # count of orders with status=PARSED (not yet entered)
    "failed_orders": int,        # count of orders with status=FAILED
    "cycle_count": int,          # how many cycles this process has run
    "timestamp": str,            # ISO 8601 UTC
}
```

Invoked via CLI: `python main.py --health` — prints JSON to stdout and exits.

## Alert Thresholds (current behavior)

Hermes does not have configurable numeric thresholds yet. The current behavior:

| Condition | Action |
|-----------|--------|
| `failed_orders > 0` after `_MAX_RETRIES` cycles | `orchestrator.escalate()` |
| Email poll raises an exception | Cycle returns early; logged at ERROR level |
| A2000 `validate()` raises on startup | Process exits; operator must intervene |

## Escalation Flow

```
1. Failure detected (exception in pipeline step OR retry count exceeded)
    ↓
2. logger.warning("ESCALATION → ...")    (always logged)
    ↓
3. EmailAgent.send_alert(to=ESCALATION_EMAIL, subject="[Hermes] Action Required")
    ↓
4. log_audit(action="escalation_sent", details={to, message})
```

If `send_alert()` itself fails, the exception is caught and logged but NOT
re-raised — the escalation failure is logged and the process continues.
This prevents an alert failure from crashing the main loop.

**WhatsApp webhook (not yet implemented):** The architecture doc references a
WhatsApp webhook as a secondary escalation path. When implemented, it should be
called after the email attempt, regardless of email success/failure, so operators
get notified even when the client's email is down.

## Required Environment Variable

```
ESCALATION_EMAIL=emmanuel@example.com
```

If `ESCALATION_EMAIL` is empty, `orchestrator.escalate()` still logs the message
but `send_alert()` will attempt to send to an empty string — this will raise an
SMTP error. Always set `ESCALATION_EMAIL` in production deployments.

## Obsidian Links
- [[brain/ARCHITECTURE]] | [[brain/CAPABILITIES]] | [[skills/self-improvement/SKILL]]
