---
description: Show current Hermes system status (orders, failures, health)
---

Run `python scripts/report_tool.py --status` and summarize the output for Emmanuel in plain English.

Include:
- Orders processed in last 24h
- Orders currently pending or failed
- Any escalations awaiting human input
- Email agent connection status
- A2000 connection status
- Any chargeback disputes with < 7 days remaining

Format as a dashboard card, not a table. Bold the numbers that need attention.