---
tags: [hermes, client]
---

# Lowinger Distribution — Deployment Notes

> First production deployment of Hermes.
> Contact: Emmanuel Lowinger (operator). Introduced by Adon.

## Client Business

Lowinger Distribution is a wholesale distributor serving large-format retail customers
including Walgreens. They receive purchase orders from buyers by email, manually enter
them into A2000, print invoices, and email them back. Hermes automates this entire loop.

**Industry:** Wholesale distribution, apparel/fashion adjacent (A2000 is GCS apparel ERP)
**Order volume:** TBD — confirm with Emmanuel in discovery. Estimate: 10–50 POs/day.
**Peak periods:** Unknown. Ask Emmanuel if there are seasonal spikes.

## POS System

**System:** A2000 by GCS Software — apparel/fashion ERP and POS
**Version:** TBD — confirm during discovery call
**Modules licensed:** TBD — specifically need to confirm EDI module availability
**Access method:** Start on `mock`, move to `edi` once EDI module confirmed, evaluate
  `api` if GCS can provide REST credentials

## Email Stack

**Provider:** TBD — Emmanuel uses Outlook, confirm whether it is hosted Microsoft 365
  (in which case IMAP is `outlook.office365.com`) or on-premises Exchange.
**MFA:** If Microsoft 365 MFA is enabled, `EMAIL_PASSWORD` must be an app-specific
  password, not the account password.
**Volume:** POs arrive from multiple retail buyers. Confirm whether they all go to one
  inbox or if Emmanuel uses folder rules.

## Integration Mode Roadmap

| Phase | Mode | Trigger |
|-------|------|---------|
| 1. Demo | `mock` | Default — no live systems required |
| 2. Staging | `mock` on prod hardware | Deploy on Emmanuel's machine, test with real emails and mock A2000 |
| 3. EDI (preferred) | `edi` | Once A2000 EDI module confirmed active and EDI_OUTPUT_DIR mapped to A2000 pickup folder |
| 4. API (if available) | `api` | If GCS Software provides REST API credentials |

## Key Contacts

| Person | Role | Contact |
|--------|------|---------|
| Emmanuel Lowinger | Client operator, primary contact | TBD |
| Adon | Introducer, PropFlow partner | — |
| Conaugh McKenna | OASIS AI, builder | conaugh@oasisai.work |

## Dates

- **Discovery call:** TBD
- **Demo date:** ~2026-04-22 (target)
- **Go-live target:** May 2026

## Discovery Questions Still Open

See `docs/DISCOVERY_QUESTIONS.md` for the full list. Key open items:
- A2000 version and EDI module status
- Outlook/Exchange hosting type and MFA status
- Typical PO formats (PDF? Excel? EDI?)
- Buyer-specific PO quirks (Walgreens has custom EDI requirements)
- Current time per order (baseline for ROI calculation)

## Obsidian Links
- [[clients/README]] | [[brain/HERMES]] | [[brain/CAPABILITIES]]
