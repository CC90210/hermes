---
mutability: GOVERNED
tags: [hermes, brain, routing]
---

# Hermes — Quick Reference (Intent → Tool)

> Use this table to route any request to the right CLI tool.

## Intent → CLI Tool

| What Emmanuel Says | Tool | Command |
|---|---|---|
| "What came in overnight?" / "Show me today's orders" | report_tool.py | `python scripts/report_tool.py --daily-brief` |
| "System status" / "How many orders failed?" | report_tool.py | `python scripts/report_tool.py --status` |
| "Show me stuck/pending orders" | report_tool.py | `python scripts/report_tool.py --stuck` |
| "AR aging" / "Who owes us money?" | report_tool.py | `python scripts/report_tool.py --aging` |
| "Re-run order 42" / "Retry failed order" | pos_tool.py | `python scripts/pos_tool.py --re-run <id>` |
| "What's the status of order 42?" | pos_tool.py | `python scripts/pos_tool.py --status <id>` |
| "List today's A2000 orders" | pos_tool.py | `python scripts/pos_tool.py --list-today` |
| "Parse this PO file" | po_tool.py | `python scripts/po_tool.py --parse <file>` |
| "List all POs" / "Show failed POs" | po_tool.py | `python scripts/po_tool.py --list [--status failed]` |
| "Show PO detail for order 42" | po_tool.py | `python scripts/po_tool.py --show 42` |
| "Draft a quote for Walgreens" | quote_tool.py | `python scripts/quote_tool.py --customer "Walgreens" --interactive` |
| "Show saved quotes" | quote_tool.py | `python scripts/quote_tool.py --list` |
| "Look up Walgreens account" / "Show me Sysco's history" | customer_tool.py | `python scripts/customer_tool.py --lookup "Walgreens"` |
| "Show all customers" | customer_tool.py | `python scripts/customer_tool.py --list` |
| "Check inbox" / "Any new emails?" | email_tool.py | `python scripts/email_tool.py --list-inbox` |
| "Show drafts" | email_tool.py | `python scripts/email_tool.py --list-drafts` |
| "Send draft <id>" | email_tool.py | `python scripts/email_tool.py --send-draft <id> --confirm` |
| "Show invoice history" / "Resend invoice" | invoice_tool.py | `python scripts/invoice_tool.py --list [--order-id X]` |
| "Chargebacks" / "What chargebacks do we have open?" | chargeback_tool.py | `python scripts/chargeback_tool.py --list-open` |
| "Add chargeback" | chargeback_tool.py | `python scripts/chargeback_tool.py --add` |
| "Draft dispute for CB-xxx" | chargeback_tool.py | `python scripts/chargeback_tool.py --draft-dispute <id>` |
| "Is the pipeline running?" / "Health check" | health_tool.py | `python scripts/health_tool.py` |
| "End of session" / session close | state_sync.py | `python scripts/state_sync.py --note "..."` |

## Slash Commands (Claude Code)

| Command | What it does |
|---|---|
| `/status` | Dashboard card: orders, failures, escalations |
| `/daily-briefing` | Morning briefing — orders overnight, failures, chargebacks |
| `/process-pending` | Manual orchestrator cycle (`main.py --once`) |
| `/re-run-order <id>` | Re-queue a failed order |
| `/quote <customer>` | Interactive quote builder |
| `/chargebacks` | Open chargebacks with dispute windows |
| `/customer <name>` | Full customer profile |
| `/draft-email <to> <topic>` | Draft email for Emmanuel's approval |

## Obsidian Links
- [[brain/HERMES]] | [[brain/CAPABILITIES]] | [[brain/AGENTS]]
