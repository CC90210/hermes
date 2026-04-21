---
mutability: FREELY-MUTABLE
tags: [hermes, memory, customers, compliance]
---

# Hermes — Customer Profiles

> One section per customer. Includes compliance requirements, quirks, preferences, and chargeback history.
> Updated from: Emmanuel's corrections, email thread patterns, chargeback deductions.

---

## Template

```
### [Customer Name] — [Account Type]
**EDI trading partner ID:** TBD
**Routing:** DSD (Direct Store Delivery) | DC (Distribution Center) | Both
**PO format:** PDF | Excel | EDI X12 850 | Email body
**ASN required:** YES | NO | UNKNOWN
**Label spec:** GS1-128 ZPL | GS1-128 PDF | None
**Compliance notes:** [Specific requirements that affect chargebacks]
**Known quirks:** [Anything non-standard about how they send POs or expect invoices]
**Chargeback history:** [Any patterns from past deductions]
**Last updated:** YYYY-MM-DD
```

---

## Walgreens — Primary Buyer

**EDI trading partner ID:** TBD (discovery question DISC-003 open)
**Routing:** TBD — DSD vs DC split unknown. Affects ASN structure significantly.
**PO format:** TBD — likely EDI X12 850 for DC, possibly PDF for DSD
**ASN required:** YES — EDI 856 Advance Ship Notice required before shipment
**Label spec:** GS1-128 carton labels (ZPL for Zebra thermal printer) — SSCC-18 required
**Compliance notes:**
- Walgreens Cost Recovery Program: automatic chargebacks for non-compliance
- ASN must be transmitted BEFORE shipment departs (not after)
- ASN transmission window: TBD (confirm with Emmanuel — typically 4–24h before ship)
- Carton labels must match ASN SSCC-18 exactly
- Invoice must reference original PO number exactly as written in the PO
- EDI 997 Functional Acknowledgement may be required for received 850s
**Known quirks:** TBD — awaiting real PO samples (DISC-004)
**Chargeback history:** No history yet (Hermes not yet live). Tracking to begin on first shipment.
**Last updated:** 2026-04-18

---

*New customers added here when their first PO is processed.*
*Update quirks and compliance notes from real order history — not assumptions.*

## Obsidian Links
- [[brain/EMMANUEL]] | [[memory/DECISIONS]] | [[memory/LONG_TERM]]
- [[brain/CAPABILITIES]] | [[brain/AGENTS]]
