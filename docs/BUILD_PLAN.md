# Hermes — Build Plan
**OASIS AI Solutions | Prepared for Emmanuel Lowinger | April 2026**

---

## Executive Summary

Hermes (Agent Operating System) is a fully local, AI-powered automation layer that sits between your email inbox and A2000 POS — processing purchase orders from clients like Walgreens end-to-end with zero manual intervention. When a PO arrives in Outlook, the system reads it, extracts every line item, enters the order directly into A2000, retrieves the generated invoice, and emails a confirmation back to the buyer — all within minutes, not hours. The operator never touches the keyboard for routine orders.

This matters because your business runs on speed and accuracy. A missed PO, a mis-keyed quantity, or a slow invoice turnaround costs real money and client trust. Hermes eliminates all three failure modes simultaneously: it is faster than any human entry clerk, more accurate (no transcription errors), and available 24/7 including nights, weekends, and trade show weeks. The result is a business that processes orders while you are on the floor closing the next deal.

---

> ### Why This Matters — The Chargeback Math
>
> Walgreens launched a formal **Cost Recovery Program in 2018** that automatically fines vendors weekly
> for non-compliance. It runs on their SAP system via SPS Commerce — not discretionary, not manually
> administered. For a small-to-mid wholesaler operating without a proper compliance stack, the
> annual chargeback exposure runs **$50,000–$150,000/year**.
>
> The single largest source: **late or missing Advance Ship Notices (EDI 856)**. Walgreens requires
> an ASN 4 hours before DC delivery and 1 hour before direct store delivery. Missing those windows
> triggers an automatic fine even when the physical shipment arrives on time.
>
> The second largest: **ASN/carton label data mismatch** — the SSCC-18 number on the physical
> carton label does not match the ASN file. Every carton that mismatches generates its own fine.
>
> This means the first version of Hermes that only automates PO entry — without the compliance
> layer — does not reduce liability. It increases velocity into the same chargeback surface.
> Phases 2b through 4b address this directly.
>
> **Sources:** SPS Commerce — Disputing Walgreens Compliance Fines; SupplierWiki — How to Dispute
> Deductions at Walgreens; Cleo — EDI Order to Cash Overview; JASCI Cloud — Retail Compliance
> Labels Guide.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          HERMES — DATA FLOW                          │
└─────────────────────────────────────────────────────────────────────┘

  INBOUND                  PROCESSING                    OUTBOUND
  ─────────                ──────────                    ────────

  Outlook Inbox            ┌──────────────┐              A2000 POS
  ┌──────────┐             │  Email Agent │              ┌──────────┐
  │ PO Email │────────────▶│  - Classify  │─────────────▶│  Order   │
  │ (PDF/EDI)│             │  - Extract   │              │  Entry   │
  └──────────┘             │  - Validate  │              └────┬─────┘
                           └──────┬───────┘                   │
                                  │                            │ Invoice
                           ┌──────▼───────┐              ┌────▼─────┐
                           │  Parser /    │              │ Invoice  │
                           │  Normalizer  │              │ Retrieval│
                           │  (Ollama LLM)│              └────┬─────┘
                           └──────┬───────┘                   │
                                  │                            │
                           ┌──────▼───────────────────────────▼──────┐
                           │              Manager Bot                  │
                           │  Orchestrates agents, handles errors,     │
                           │  escalates to operator when needed        │
                           └──────┬───────────────────────────────────┘
                                  │
                           ┌──────▼───────┐
                           │  Audit Log   │              Outlook Sent
                           │  (SQLite,    │              ┌──────────┐
                           │   encrypted) │─────────────▶│ Invoice  │
                           └──────────────┘              │  Email   │
                                                         └──────────┘

  ALL PROCESSING STAYS ON YOUR MACHINE. NOTHING LEAVES YOUR NETWORK.
```

---

## Phase Breakdown

### Phase 0: Discovery (Days 1–2)
**Goal:** Confirm every integration point before writing a line of code.

| Task | Owner | Output |
|------|-------|--------|
| A2000 API access confirmed or admin credentials obtained | Emmanuel + OASIS | API credentials or admin login |
| Outlook connection method confirmed (365 OAuth or IMAP) | Emmanuel | Email credentials |
| 3–5 sample POs collected (PDF, Excel, or EDI) | Emmanuel | Sample files |
| A2000 database type confirmed (Oracle) | GCS/Emmanuel | DB connection string |
| A2000 EDI module license status confirmed | Emmanuel + GCS | Active transaction sets list |
| Walgreens chargeback exposure baseline established | Emmanuel | Annual $ estimate or recent quarter |
| Setup call — 30 minutes to walk through one full order manually | Both | Process map |

**Exit Criteria:** We can connect to the inbox and open A2000. We have seen at least one real PO. We know whether the EDI module is active.

---

### Phase 1: Email Agent (Days 3–5)
**Goal:** Reliable inbox monitoring and structured PO extraction.

- Connect to Outlook via Microsoft Graph API (365) or IMAP (on-prem)
- Monitor inbox for new PO emails from known sender domains (Walgreens, etc.)
- Classify emails: PO, PO update, cancellation, inquiry (non-PO filtered out)
- Extract structured data from attachments: PDF parsing, Excel ingestion, EDI 850 parsing
- Normalise all POs into a common schema: `{po_number, buyer, ship_date, line_items[]}`
- Write to local SQLite queue with status tracking
- Alert operator on unknown format (new sender, unusual attachment type)

**Deliverable:** Agent that reads inbox every 5 minutes, parses POs, writes to queue. Tested against all 5 sample POs.

**Estimate:** ~5 days / ~12 hours billable

---

### Phase 2: POS Integration (Days 5–8)
**Goal:** Orders entered into A2000 without manual keyboard input.

Integration approach chosen in priority order (confirmed during Phase 0):

| Tier | Method | Reliability | Notes |
|------|--------|-------------|-------|
| 1 | A2000 REST API | Highest | Cleanest if GCS has exposed endpoints |
| 2 | EDI 850 import | High | Standard wholesale format — A2000 supports natively |
| 3 | Direct DB write | Medium | Risky without schema docs — use only if tiers 1–2 unavailable |
| 4 | Screen automation (Playwright) | Lower | Pixel-perfect entry via UI — reliable but brittle on UI updates |

- Map PO schema fields to A2000 order entry fields
- Handle line item matching: SKU lookup, unit conversion, pricing validation
- Post order to A2000, capture order confirmation number
- Update SQLite queue: `{status: "entered", a2000_order_id, timestamp}`
- On failure: retry 3x, then escalate to operator via email alert

**Deliverable:** End-to-end order entry for all 5 sample POs, logged and confirmed in A2000.

**Estimate:** ~3 days / ~8 hours billable

---

### Phase 2b: ASN + Carton Labels — PRE-LAUNCH FOR WALGREENS (Days 8–18)
**Goal:** Every Walgreens shipment leaves the dock with a valid ASN transmitted and GS1-128 labels on every carton — eliminating the #1 source of automatic chargeback fines.

**Why this cannot be skipped:** Without an ASN, every Walgreens shipment triggers an automatic fine under the Cost Recovery Program regardless of whether the product arrives on time. Without matching GS1-128 carton labels, even a correct ASN generates a data-mismatch chargeback. These are not enhancements — they are pre-conditions for the system not creating new liability.

#### EDI 856 ASN Generation
- Build hierarchical ASN structure per ANSI X12 5010 specification: shipment (BSN) → order (PRF) → tare (HL) → pack (HL) → item (LIN/SN1)
- Each carton assigned a unique SSCC-18 Serial Shipping Container Code
- SSCC computed as: extension digit + GS1 Company Prefix + serial reference + Modulo-10 check digit
- ASN data elements: SSCC per carton, PO number, ship-to DC location (GLN), vendor ID, carton count, item GTINs, quantities
- ASN file and physical carton label must carry identical SSCC data — mismatch is an automatic chargeback

#### ASN Transmission Timing Logic
- Walgreens DC (Distribution Center): ASN must be transmitted at least **4 hours before truck arrival**
- Walgreens DSD (Direct Store Delivery): ASN must be transmitted at least **1 hour before truck arrival**
- Hermes triggers ASN transmission from the packing confirmation event, not the ship event
- If ship_date/time is unknown: escalate to operator before transmission window closes

#### GS1-128 / SSCC-18 Carton Label Output
- Label format: 4" × 6" thermal, GS1-128 barcode symbology (Code 128), minimum 203 DPI
- Required data elements per Walgreens spec: SSCC-18 with AI (00), PO Number with AI (400), ship-to DC with AI (410), vendor number, carton count
- Primary output: ZPL string for Zebra thermal printers (zero PDF rendering overhead at dock)
- Fallback output: PDF for shops without a Zebra printer
- Barcode height: minimum 1 inch; 0.25" quiet zones required

**Implementation module:** `adapters/edi_856_asn.py` (skeleton exists), `adapters/gs1_128_label.py` (skeleton exists)

**Deliverable:** ASN generated and test-transmitted for 3 sample shipments. Labels printed on thermal printer and verified by scan.

**Estimate:** ~7–10 days / ~20–25 hours billable

---

### Phase 3: Invoice Loop (Days 18–21)
**Goal:** Invoice automatically retrieved and emailed to buyer after order is confirmed.

- Poll A2000 for invoice generation after order confirmation (or trigger via webhook if API supports)
- Retrieve invoice as PDF
- Compose outbound email to buyer: professional template, invoice attached, PO number referenced
- Send via Outlook (same connected account — replies stay in your thread history)
- Log sent timestamp, recipient, invoice number
- Confirmation back to operator: "Invoice #12345 sent to Walgreens buyer@walgreens.com — 4 minutes after PO received"

**Deliverable:** Invoice emailed to buyer within 10 minutes of PO receipt, zero manual steps.

**Estimate:** ~3 days / ~8 hours billable

---

### Phase 3b: PO Acknowledgment (EDI 855) — PRE-LAUNCH (Days 21–25)
**Goal:** Walgreens receives an EDI 855 acknowledgment within the 24–48 hour window for every PO. Missing this flags the vendor in Walgreens' compliance system before the first box ships.

#### Three Response Modes
- **Accept-as-is:** PO matches contract pricing, all SKUs valid, inventory allocatable — auto-ack without human review
- **Accept-with-changes:** Price mismatch, quantity adjustment, or ship-date shift — generate 855 with change segments, escalate to operator before transmission
- **Reject:** SKU not found, customer on credit hold, PO structurally invalid — escalate immediately with reason code

#### Auto-Ack Logic
- Clean PO (no mismatches detected by Phase 4b pricing/credit checks): transmit 855 Accept automatically within 2 hours of receipt
- Any mismatch detected: hold for operator review, notify within 15 minutes of detection
- Transmission method: EDI VAN or AS2 connection (confirmed during Phase 0)

**Implementation module:** `adapters/edi_855_ack.py` (skeleton exists)

**Deliverable:** 855 transmitted for 5 test POs across all three response modes.

**Estimate:** ~3–5 days / ~10 hours billable

---

### Phase 4: Manager Bot (Days 25–27)
**Goal:** Orchestration layer that runs the full loop autonomously and handles failures gracefully.

- Supervises all agents: Email Agent, Parser, POS Adapter, ASN Agent, Invoice Agent
- Health checks every 15 minutes: Are all agents running? Is A2000 reachable? Is inbox connected?
- Retry logic: Transient failures (network, A2000 timeout) retried automatically with exponential backoff
- Escalation matrix: After 3 failed retries, operator notified via email with full context (which PO, what error, what to do)
- Daily summary email to operator: orders processed, ASNs transmitted, errors, time saved
- Graceful shutdown and restart support

**Deliverable:** System runs unattended. You only receive emails when something genuinely needs your attention.

**Estimate:** ~3 days / ~10 hours billable (extended from original to account for ASN/label health monitoring)

---

### Phase 4b: Pricing & Credit Validation — PRE-LAUNCH (Days 27–32)
**Goal:** Hermes never enters an order with a pricing mismatch or against a buyer on credit hold. Silent wrong entries are worse than a held order — they create deductions on the 820 remittance 30–60 days later with no paper trail.

#### Contract Price Lookup
- Pull customer-specific price list from A2000 pricing tables per buyer
- Apply volume tier logic: quantity thresholds trigger price breaks
- Apply promotional pricing: time-bounded overrides where applicable
- Mismatch handling: defer order entry, generate 855 Accept-with-changes flagging the discrepancy, alert Emmanuel

#### Credit Hold Check
- Before entering any order into A2000: check customer credit status
- Fields checked: credit_limit, current_balance, days_past_due, hold_flag
- Result states: approve (proceed), hold (queue for AR review), escalate (notify Emmanuel immediately)
- Auto-entry only proceeds on explicit "approve" result — never on ambiguous credit state

**Implementation modules:** `adapters/contract_price.py` (skeleton exists), `adapters/credit_check.py` (skeleton exists)

**Deliverable:** Pricing and credit checks integrated into the Phase 2 order entry flow. 3 test scenarios: clean order, price mismatch, credit hold.

**Estimate:** ~5 days / ~12 hours billable

---

### Phase 5b: Apparel Matrix Parser — PRE-LAUNCH IF APPAREL SKUs PRESENT (Conditional, ~5 days)
**Goal:** Walgreens apparel POs arrive as size-color matrices, not flat line items. A generic parser silently produces wrong order entries. This phase prevents that.

#### The Problem
A Walgreens apparel PO does not say "500 units of SKU-12345." It says:

```
Style: BT-2210 | Color: NVY
XS: 50 | S: 100 | M: 150 | L: 120 | XL: 80 | XXL: 50
```

That is one line in the PO representing 550 units across 6 distinct SKUs. Entered incorrectly, it becomes a short-ship or mis-pick — both generate chargebacks.

#### Detection and Expansion
- Detect matrix format in incoming PO text before passing to standard parser
- Expand matrix to per-SKU line items: one A2000 order line per size-color combination
- Cross-reference buyer item codes (Walgreens internal item IDs) to vendor style numbers in A2000
- Validate every expanded SKU has a UPC/GTIN — required for GS1-128 label generation in Phase 2b
- Season code validation: confirm order is against an open season in A2000

**Implementation module:** `adapters/matrix_expander.py` (skeleton exists)

**Deliverable:** Matrix expansion tested against 3 sample apparel POs. All expanded SKUs validated against A2000 item master.

**Estimate:** ~5 days / ~12 hours billable (conditional on confirming apparel SKUs in discovery)

---

### Phase 6b: Remittance Reconciliation — PRE-SECOND-CLIENT (~5 days)
**Goal:** When Walgreens pays, the EDI 820 tells you which invoices are paid and which deductions are taken. Without parsing this, Emmanuel reconciles payment manually against open invoices — and deductions land silently in the bank balance.

#### EDI 820 Parsing
- Receive and parse EDI 820 Remittance Advice from Walgreens
- Extract: payment amount, invoice references, deduction details (type, amount, reason code)
- Deduction types tracked: MDF (co-op marketing), chargebacks, allowances, volume rebates

#### Invoice Matching
- Match 820 payment references against open invoices in SQLite
- Mark invoices as: paid-in-full, paid-with-deduction, unpaid
- Surface deductions with reason codes and invoice references for review

**Implementation module:** `adapters/edi_820_remit.py` (skeleton exists)

**Deliverable:** 820 parsing tested against 3 sample remittance files. Deductions surfaced in operator report.

**Estimate:** ~5 days / ~12 hours billable

---

### Phase 7b: Chargeback Dispute Tracking — PRE-SECOND-CLIENT (~7 days)
**Goal:** Track every deduction Walgreens takes, countdown the 4-week dispute window, and alert Emmanuel before money is permanently forfeited. Walgreens's 4-week dispute window is firm — no exceptions.

#### Detection and Tracking
- New deductions detected from 820 within 24 hours of file receipt
- Deduction logged as ChargebackEvent: type, amount, detection date, dispute_window_closes_at
- Status states: OPEN → UNDER_DISPUTE → CLOSED or REVERSED

#### Dispute Window Countdown
- Days remaining in 4-week window calculated daily
- Alert thresholds: 14 days remaining (initial alert), 7 days (urgent), 3 days (escalate to phone/WhatsApp)

#### Auto-Draft Dispute Submission
- On operator request: draft dispute email to SupplyChain.Compliance@Walgreens.com
- Include: deduction ID, invoice reference, ASN proof, POD (proof of delivery), narrative
- Valid dispute grounds: Walgreens DC pushed appointment past WSTA, insufficient lead time provided
- Dispute submitted via SupplierNet > Forms > Vendor Dispute Form (browser automation via Playwright)

**Implementation module:** `adapters/chargeback_tracker.py` (skeleton exists)

**Deliverable:** End-to-end dispute workflow tested with 2 sample chargebacks. Countdown timer verified. Auto-draft reviewed by Emmanuel.

**Estimate:** ~7 days / ~18 hours billable

---

### Phase 5: Phone Agent — Outbound IVR (Weeks 6–8, after compliance stack)
**Goal:** Handle outbound calls to buyers for order confirmation, status updates, or escalations requiring a phone call.

- Built on Twilio (voice) + Vapi (AI voice agent) or ElevenLabs (TTS)
- IVR navigation: Agent calls, presses menu options, reaches the right department
- Scripted flows: "Calling to confirm PO #12345 received and processing" — waits for confirmation, logs outcome
- Transfer to operator: If call goes to voicemail or human wants to speak to someone, routes to Emmanuel's cell

**Deliverable:** Outbound confirmation call triggered by Manager Bot for orders above a configurable threshold value.

---

### Phase 6: Self-Improvement (Ongoing)
**Goal:** System gets better every week without additional development cost.

- Parser error log reviewed by Ollama weekly: patterns in failed extractions → prompt tuning
- A2000 rejection log: recurring validation errors → field mapping updates
- Invoice delivery failures: bounce tracking → contact list hygiene
- ASN transmission failures: timing analysis → escalation threshold tuning
- Chargeback trends: pattern detection → preventive rule additions
- Monthly report to operator: throughput trends, error rate trend, chargeback rate, time saved YTD
- OASIS AI quarterly review: assess new capabilities (new PO formats, new buyers, new integrations)

---

## A2000 Integration Options — Detailed

### Tier 1: REST API (Preferred)
GCS Software (A2000 vendor) offers a REST API for enterprise customers. If your licence includes API access, this is the cleanest path — no screen scraping, no DB risk.

- **Pros:** Officially supported, stable across A2000 updates, full CRUD on orders
- **Cons:** Requires GCS to enable and provide credentials — confirm during Phase 0
- **Endpoints needed:** Create order, get order status, retrieve invoice PDF, customer credit status, contract price lookup

### Tier 2: EDI 850 Import (Reliable — also enables 855/856 path)
A2000 natively supports EDI (Electronic Data Interchange). The EDI module covers 850, 855, 856, 810, 820, 832, 846, 997 — 500+ pre-built trading partner maps including Walgreens.

- **Pros:** Industry standard, A2000 supports it natively, battle-tested in wholesale, directly unlocks the ASN and 855 workflow
- **Cons:** Requires EDI mapping setup upfront, EDI module must be licensed
- **Note:** This is the preferred long-term path regardless of REST API availability — it is the only path that gives Hermes native 856 ASN and 855 Ack transmission

### Tier 3: Direct Database Write (Risky — Fallback Only)
A2000 runs on Oracle. Direct DB writes require Oracle SQL, Oracle JDBC drivers, and navigating strict transaction semantics. GCS support contract almost certainly voids on unsanctioned writes.

- **When to use:** Only if Tiers 1 and 2 are definitively unavailable

### Tier 4: Screen Automation (Always Available)
Playwright drives A2000's UI exactly as a human would. Important limitation: screen automation cannot generate SSCC labels or transmit EDI — it is not a permanent solution for ASN compliance.

- **When to use:** Development/demo mode, or as permanent fallback for PO entry only

---

## Security Architecture

| Layer | Implementation |
|-------|---------------|
| LLM Processing | Ollama — runs 100% on your machine, no data sent to OpenAI or any cloud |
| Data Storage | SQLite with SQLCipher encryption at rest |
| Credentials | Stored in `.env` file, never committed to code, never logged |
| Network | Only outbound calls: Outlook (your own account), A2000 (local network), EDI VAN (encrypted) |
| Audit Trail | Every agent action logged: timestamp, agent, action, result |
| Access Control | System runs under your Windows user account — no elevated privileges needed |
| Support Access | OASIS AI can remote-in ONLY with your explicit permission per session |

**Data never leaves your network for processing.** The only external calls are to services you already use (your own Outlook account, your own A2000 instance, your existing EDI VAN).

---

## Cost Estimate

### Development

| Phase | Scope | Estimate | Rate (USD) | Cost |
|-------|-------|----------|-----------|------|
| Phase 0: Discovery | Integration confirmation | 4 hrs | — | Included |
| Phase 1: Email Agent | Inbox monitor + PO extraction | ~12 hrs / ~5 days | $150/hr | $1,800 |
| Phase 2: POS Integration | Order entry into A2000 | ~8 hrs / ~3 days | $150/hr | $1,200 |
| Phase 2b: ASN + Labels | EDI 856 + GS1-128 carton labels | ~20–25 hrs / ~7–10 days | $150/hr | $3,000–3,750 |
| Phase 3: Invoice Loop | Invoice retrieval + email | ~8 hrs / ~3 days | $150/hr | $1,200 |
| Phase 3b: EDI 855 Ack | PO acknowledgment | ~10 hrs / ~3–5 days | $150/hr | $1,500 |
| Phase 4b: Pricing + Credit | Validation before entry | ~12 hrs / ~5 days | $150/hr | $1,800 |
| Phase 5b: Matrix Parser | Apparel SKU expansion (conditional) | ~12 hrs / ~5 days | $150/hr | $1,800 |
| Phase 6b: 820 Reconciliation | Remittance parsing | ~12 hrs / ~5 days | $150/hr | $1,800 |
| Phase 7b: Chargeback Tracker | Dispute window tracking + auto-draft | ~18 hrs / ~7 days | $150/hr | $2,700 |
| Phase 4: Manager Bot | Orchestration layer | ~10 hrs / ~3 days | $150/hr | $1,500 |
| Phase 5: Phone Agent (optional) | Outbound IVR | ~20 hrs | $150/hr | $3,000 |
| Phase 6 setup: Self-improvement | Ongoing tuning | ~6 hrs | $150/hr | $900 |
| **Walgreens-Ready Total** | **Phases 0–4b** | **~85–90 hrs** | | **~$13,000–14,500** |
| **Full Compliance Stack** | **+ 5b + 6b + 7b** | **~115–120 hrs** | | **~$17,250–18,000** |

> **ROI framing:** If Hermes prevents $50,000/year in chargebacks and eliminates $4,000/month in data
> entry labor, the full build pays for itself in under 5 weeks. The monthly retainer after that is
> pure margin recovery.

### Infrastructure (Monthly)

| Component | Cost |
|-----------|------|
| Ollama (local LLM) | **$0** — runs on your hardware |
| SQLite | **$0** — open source |
| Cloud hosting | **$0** — runs on your machine |
| Twilio (if Phase 5) | ~$20–50/mo depending on call volume |
| EDI VAN (if not already subscribed) | ~$300–1,000/mo depending on volume and provider |
| **Total infrastructure** | **$0–50/mo** (if EDI VAN already active) |

### Monthly Maintenance Retainer
Monitoring, error triage, prompt tuning, A2000 compatibility updates, ASN timing rule updates, quarterly review call.
**$300–500/mo** depending on order volume and complexity.

---

## Timeline

```
Week 1    Week 2    Week 3    Week 4    Week 5    Week 6–8  Ongoing
────────  ────────  ────────  ────────  ────────  ────────  ────────
[P0][P1]  [P2][2b]  [P3][3b]  [P4b]─── [P4]───── [P5][5b]  [P6]────
Discovery  POS +     Invoice   Pricing   Manager   Phone +   Self-
+ Email    ASN +     Loop +    + Credit  Bot +     Matrix    Improve
Agent      Labels    855 Ack   Validation UAT      Parser
                                                   (optional)
                     ↑
               WALGREENS-READY
               (end of week 5)
```

**2-week MVP:** Email → A2000 → Invoice → Email, fully automated, zero manual steps for routine orders.
**5-week Walgreens-ready:** Full compliance stack live — ASN, labels, 855 ack, pricing validation, credit check.
**6–8 weeks full:** Remittance reconciliation, chargeback tracking, optional apparel matrix and phone agent.

> The original 2-week MVP timeline is real and still ships. The compliance phases (2b, 3b, 4b)
> run in parallel with Phase 3 and Phase 4 — they are not sequential blockers, they are scope
> additions. Realistic calendar time to Walgreens-ready: **6–8 weeks of focused work**.

---

## Success Metrics

| Metric | Baseline (Manual) | Target (Hermes) |
|--------|------------------|-------------|
| Orders processed per day | Limited by staff hours | Unlimited (24/7) |
| Time per order (receipt to entry) | 10–20 minutes | < 5 minutes |
| Invoice turnaround | 1–24 hours | < 10 minutes |
| Entry error rate | ~2–5% (human) | < 0.5% |
| Staff time on PO entry | 2–4 hrs/day | 0 hrs/day |
| Orders processed after hours | 0 | 100% |
| ASN transmission rate | Manual / ad-hoc | 100% before transmission window |
| Chargeback rate (Walgreens) | $50K–$150K/yr exposure | Target: <$5K/yr |
| Dispute capture rate | Near 0% (manual, missed windows) | >90% of disputable deductions |

**The headline number:** If you process 20 orders/day at 15 minutes each, that is 5 hours of daily
manual work eliminated — every day, permanently. If Hermes prevents even one missed ASN transmission
per week at Walgreens, the chargeback savings alone fund 3 months of the retainer.
