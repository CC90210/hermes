---
description: Show all open chargebacks with dispute windows
---

Run `python scripts/chargeback_tool.py --list-open` and format output as:
- Total open chargeback amount
- Each with: retailer, amount, days remaining, dispute status, recommended action
- Flag any with < 7 days as URGENT