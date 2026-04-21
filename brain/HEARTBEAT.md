---
mutability: SEMI-MUTABLE
tags: [hermes, brain, monitoring, heartbeat]
---

# HEARTBEAT — Proactive Health Monitoring

> Hermes checks system health continuously, not just when asked.
> These checks run at session start and on a cron schedule when the background daemon is active.

## Session-Start Checks (IDE Mode)

Run these in order before responding to Emmanuel's first request.

### 1. Memory Consistency (Priority: HIGH)
```
CHECK:
- ACTIVE_TASKS.md — any tasks left OPEN or BLOCKED from the last session?
- SESSION_LOG.md (last 3 entries) — any incomplete work?
- MISTAKES.md — any recent mistakes that apply to today's work type?
- PATTERNS.md — any [PROBATIONARY] items ready for promotion (3+ successful uses)?

ACTION:
- Flag stale open tasks to Emmanuel
- Carry forward or close them
- Promote probationary patterns that have hit the threshold
```

### 2. Pipeline Health (Priority: HIGH)
```
CHECK (python scripts/health_tool.py):
- email_connected: IMAP connection alive?
- a2000_reachable: A2000 client responding?
- pending_orders: any orders in PARSED status (not yet entered)?
- failed_orders: any orders in FAILED status?

THRESHOLDS:
- pending_orders > 10: alert Emmanuel — potential backlog
- failed_orders > 0: surface each one with reason
- email_connected = False: surface immediately, pipeline is blind
- a2000_reachable = False: pipeline is blocked, escalate

ACTION:
- Report any non-zero failures or connection issues before starting work.
- Do not start a new cycle if failed_orders > 5 without reviewing them first.
```

### 3. Stale Escalations (Priority: HIGH)
```
CHECK (brain/STATE.md — active escalations section):
- Any escalations older than 24 hours without a response?

ACTION:
- Re-surface to Emmanuel: "Still waiting on your reply for {po_number} — {specific_question}."
- Do not re-escalate identical content more than once per day (alert fatigue).
```

### 4. Chargeback Window Alerts (Priority: HIGH — time-sensitive)
```
CHECK (python scripts/chargeback_tool.py --list-open):
- Any open chargebacks with dispute window < 72 hours?

THRESHOLDS:
- < 72h remaining: notify Emmanuel immediately
- < 24h remaining: urgent alert, surface at session start regardless of other work

ACTION:
- Surface the specific chargeback ID, customer, amount, deadline.
- Ask Emmanuel: "Do you want me to draft the dispute email now?"
```

### 5. Pending Tasks Review (Priority: MEDIUM)
```
CHECK (memory/ACTIVE_TASKS.md):
- Overdue items (tasks with dates that have passed)?
- Blocked items (waiting on external info from Emmanuel)?

ACTION:
- Present blocked items. Ask Emmanuel for the missing info.
- Do not silently carry stale tasks across more than 3 sessions.
```

## Continuous Checks (Background Daemon Mode)

When `python main.py` is running as a daemon, these checks fire on schedule:

| Interval | Check | Alert Threshold |
|----------|-------|----------------|
| Every cycle (5 min default) | email_connected, a2000_reachable, pending_orders, failed_orders | Any False or > 5 failed |
| Every hour | Chargeback dispute windows | < 72 hours remaining |
| Every 24 hours | Stale FAILED orders | FAILED orders > 24h without progress |
| Every 24 hours | Audit log write rate | < 1 entry per hour during business hours |
| Every 7 days | Pattern drift | Error rate increasing over prior week? |
| Every 7 days | New customer not profiled | Customer in orders not in CUSTOMERS.md |

## Daily Health Checks (Morning Session Start)

Run `python scripts/report_tool.py --daily-brief` to get:
- Orders processed overnight
- Failed orders requiring review
- Open chargebacks and window countdowns
- Any system connection issues

## Duplicate Suppression

If the same issue was surfaced in the last session and Emmanuel has not acted:
- Don't repeat the full alert verbatim.
- Instead: "Still unresolved from last session: {issue}. Priority: {level}."

This prevents alert fatigue without letting issues disappear.

## Heartbeat Report Format (Session Start)

```
HEARTBEAT — {date}
- Pipeline: {OK | ISSUES FOUND} ({N} pending, {N} failed)
- Email: {CONNECTED | DISCONNECTED}
- A2000: {REACHABLE | UNREACHABLE}
- Chargebacks: {N open, {N} urgent (<72h)}
- Open tasks: {N items, {N} blocked}
- Patterns ready to promote: {N}
Ready, Emmanuel.
```

Only report items that need attention. Don't dump a wall of OKs.

## Obsidian Links
- [[brain/INTERACTION_PROTOCOL]] | [[brain/BRAIN_LOOP]] | [[brain/STATE]]
- [[memory/ACTIVE_TASKS]] | [[memory/SESSION_LOG]] | [[brain/CAPABILITIES]]
