---
tags: [hermes, brain, client-profile]
---

# EMMANUEL — Client Profile

> Hermes reads this to understand Emmanuel Lowinger's world. Update as more context is gathered.

## Identity

- **Full Name:** Emmanuel Lowinger
- **Company:** Lowinger Distribution
- **Role:** Operator / Owner (wholesale distributor)
- **Location:** TBD (confirm during Day 1)
- **Introduced by:** Adon (PropFlow partner)

## Business Context

Lowinger Distribution is a wholesale distributor serving large-format retail buyers including Walgreens. Emmanuel currently handles the full PO-to-invoice loop manually: receiving POs by email, entering them into A2000, printing invoices, and emailing them back. This is what Hermes automates.

**Order volume:** TBD (estimate 10-50 POs/day — confirm with Emmanuel)
**Primary buyer:** Walgreens (EDI compliance critical — automatic chargebacks under Cost Recovery Program)
**A2000 version:** TBD — confirm EDI module status
**Email stack:** Outlook / Microsoft 365 (confirm IMAP vs Graph API)

## Working Style

- Direct communicator. No fluff.
- Wholesale operator — not a developer. Prefers canned commands over raw prompts.
- Time-sensitive: orders must process before end-of-day or buyers escalate.

## What Hermes Does NOT Decide for Emmanuel

- Pricing changes
- Credit limit adjustments
- Order cancellations
- Any customer-facing communication (Hermes drafts, Emmanuel approves)
- New customer terms

## Open Discovery Questions

1. A2000 version and EDI module status
2. Outlook/Exchange hosting type and MFA status
3. Typical PO formats (PDF? Excel? EDI?)
4. Walgreens-specific EDI requirements (ASN 856, labels, etc.)
5. How many people at Lowinger will touch Hermes?
6. Claude API billing preference: Lowinger pays, or baked into OASIS retainer?

## Obsidian Links
- [[brain/HERMES]] | [[brain/PRINCIPLES]] | [[clients/lowinger/README]]
