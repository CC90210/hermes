# HERMES — Your Quick-Start Guide

> This is written for you, Emmanuel. Keep it pinned in your IDE or printed next to your monitor.

## What Hermes Does For You (in one paragraph)

Hermes is your commerce agent. Think of him as a team member who never sleeps. He reads your inbox for POs, enters orders into A2000, sends invoices back to customers, keeps you compliant with Walgreens' EDI and labeling requirements, tracks chargebacks you can dispute, and answers questions when you ask. Everything he does is logged. Everything he does stays on your computer. You never lose control — you can always override him, pause him, or ask him to show you what he did.

## The Two Hermeses

You have two ways to interact with Hermes:

1. **Background Hermes** — runs automatically on a schedule. Processes POs, sends invoices, does the routine work. You don't talk to this one; he just works.

2. **IDE Hermes** — the one you TALK to. Open Claude Code, and he's right there. You type or say things like "Hey Hermes, what came in overnight?" and he answers and acts.

Both are the same Hermes — same memory, same data. The difference is one runs on autopilot, the other runs when you ask.

## Day One — What To Try First

1. Open Claude Code (you should see "Hermes" in the banner).
2. Type: `/status`
3. Hermes replies with your system dashboard: how many POs processed today, any failures, chargebacks to watch.
4. Type: `/daily-briefing`
5. Hermes gives you a 5-bullet morning brief.

That's it. Keep going with the prompts below as you get comfortable.

## Talking to Hermes — Example Prompts

Copy these verbatim or adapt them.

### For Order Operations
- `Hey Hermes, what POs came in since last night?`
- `Hermes, pull up order MOCK-069E55CA and show me what happened.`
- `Re-run the failed order from this morning.`
- `Was PO #12345 from Walgreens acknowledged with an 855 yet?`
- `Show me every order that's been in "failed" status for more than 2 hours.`

### For Customer Questions
- `Hermes, tell me everything about the Walgreens account — credit status, open AR, last 5 orders, any red flags.`
- `What's the trend on Walgreens order volume this month vs last?`
- `Who are my top 3 customers by dollar volume this quarter?`
- `Has anyone from Walgreens corporate emailed me in the last week?`

### For Drafting
- `Hermes, draft an email to purchasing@walgreens.com asking about PO #12345 shipping confirmation. Use my voice — direct, no fluff.`
- `Draft a quote for 500 units of SKU LWG-1001 at our 5% volume tier. Save it to drafts, don't send.`
- `Write a dispute email for the $340 chargeback from last week — the one for late ASN. Pull the supporting data.`

### For Chargebacks and Compliance
- `Hermes, any chargebacks with less than a week left on the dispute window?`
- `Show me every deduction Walgreens has taken in the last 90 days. Total it up.`
- `Is my ASN generation running clean? Any late transmissions this week?`

### For Status and Reports
- `/status`
- `/daily-briefing`
- `/chargebacks`
- `Give me a weekly summary of order value, errors, and chargebacks.`
- `What's my error rate on PO parsing this month?`

## Slash Commands (Shortcuts)

These are quick commands for things you'll ask a lot:

| Command | What it does |
|---|---|
| `/status` | Current system health + order counts |
| `/daily-briefing` | Your 5-bullet morning brief |
| `/process-pending` | Manually trigger a PO processing cycle |
| `/re-run-order <id>` | Retry a failed order |
| `/chargebacks` | Open chargebacks with dispute deadlines |
| `/quote <customer>` | Start an interactive quote builder |
| `/customer <name>` | Full customer profile lookup |
| `/draft-email <to> <topic>` | Draft an email in your voice |

## What Hermes Will NEVER Do Without Asking You

1. Send an email without you approving the draft
2. Cancel an order
3. Change a customer's credit limit
4. Modify a price outside your contract table
5. Acknowledge a PO with changes (he'll escalate — you decide)
6. Submit a chargeback dispute (he drafts it, you review and send)

## What Hermes Handles Automatically (Background)

1. Polling your inbox for new POs (every 5 minutes)
2. Parsing POs (PDF, Excel, EDI, plain text)
3. Entering orders into A2000 (mock mode during trial)
4. Retrieving invoices from A2000
5. Sending invoice emails back to customers
6. Logging every single action with timestamp
7. Alerting you when anything needs human judgment

## When Something Goes Wrong

Hermes never fails silently. If he can't do something, he'll:

1. Stop (not guess)
2. Log the failure with full detail in `memory/SESSION_LOG.md`
3. Email you (or WhatsApp, depending on how you set it up)
4. Wait for your input

To ask him what went wrong: `Hey Hermes, what happened with order 47? Walk me through the whole log.`

## Your Daily Rhythm (Recommended)

**Morning (5 min):** `/daily-briefing` → glance at the summary → handle anything flagged → coffee.

**Midday (2 min):** `/status` → confirm nothing's on fire → get back to sales.

**End of day (5 min):** `/chargebacks` → check anything with close deadlines → ask Hermes to draft any dispute emails you need → review/send tomorrow morning.

Total time with Hermes per day: ~12 minutes. Everything else is automatic.

## Getting More Out Of Hermes Over Time

Hermes gets smarter as we use him:
- When you correct him, he remembers.
- When you add new customers, he adapts.
- When we find new patterns (new retailers, new compliance rules), we add them.

Every 30 days, we'll review together: what's working, what's not, what new capability would save you the most time next. He's built to grow with the business.

## If You're Stuck

1. Type `help` — Hermes explains options for your current context.
2. Check `memory/SESSION_LOG.md` — see what he's been doing.
3. Text Conaugh (or the OASIS AI WhatsApp group) — we're here.

## One Thing To Remember

Hermes is your team member, not your tool. Talk to him like you'd talk to a sharp new hire. Be direct. Ask for outcomes, not steps. Trust him with the routine so you can focus on the relationships and the deals.

That's the whole point.

— OASIS AI (Conaugh + Adon)
