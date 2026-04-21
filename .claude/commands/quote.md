---
description: Draft a quote for a customer
---

Use $ARGUMENTS as the customer identifier. Run:
`python scripts/quote_tool.py --customer "$ARGUMENTS" --interactive`

Walk Emmanuel through:
1. Customer lookup (pricing history, credit status, past orders)
2. Product selection
3. Price calculation with any applicable discounts
4. Draft quote email
5. Save to drafts/ folder; do NOT send without explicit approval