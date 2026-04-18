# Hermes — Build Plan
**OASIS AI Solutions | Prepared for Emmanuel Lowinger | April 2026**

---

## Executive Summary

Hermes (Agent Operating System) is a fully local, AI-powered automation layer that sits between your email inbox and A2000 POS — processing purchase orders from clients like Walgreens end-to-end with zero manual intervention. When a PO arrives in Outlook, the system reads it, extracts every line item, enters the order directly into A2000, retrieves the generated invoice, and emails a confirmation back to the buyer — all within minutes, not hours. The operator never touches the keyboard for routine orders.

This matters because your business runs on speed and accuracy. A missed PO, a mis-keyed quantity, or a slow invoice turnaround costs real money and client trust. Hermes eliminates all three failure modes simultaneously: it is faster than any human entry clerk, more accurate (no transcription errors), and available 24/7 including nights, weekends, and trade show weeks. The result is a business that processes orders while you are on the floor closing the next deal.

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
| A2000 database type confirmed (Oracle or SQL Server) | GCS/Emmanuel | DB connection string |
| Setup call — 30 minutes to walk through one full order manually | Both | Process map |

**Exit Criteria:** We can connect to the inbox and open A2000. We have seen at least one real PO.

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

---

### Phase 3: Invoice Loop (Days 8–10)
**Goal:** Invoice automatically retrieved and emailed to buyer after order is confirmed.

- Poll A2000 for invoice generation after order confirmation (or trigger via webhook if API supports)
- Retrieve invoice as PDF
- Compose outbound email to buyer: professional template, invoice attached, PO number referenced
- Send via Outlook (same connected account — replies stay in your thread history)
- Log sent timestamp, recipient, invoice number
- Confirmation back to operator: "Invoice #12345 sent to Walgreens buyer@walgreens.com — 4 minutes after PO received"

**Deliverable:** Invoice emailed to buyer within 10 minutes of PO receipt, zero manual steps.

---

### Phase 4: Manager Bot (Days 10–12)
**Goal:** Orchestration layer that runs the full loop autonomously and handles failures gracefully.

- Supervises all agents: Email Agent, Parser, POS Adapter, Invoice Agent
- Health checks every 15 minutes: Are all agents running? Is A2000 reachable? Is inbox connected?
- Retry logic: Transient failures (network, A2000 timeout) retried automatically with exponential backoff
- Escalation matrix: After 3 failed retries, operator notified via email with full context (which PO, what error, what to do)
- Daily summary email to operator: orders processed, errors, time saved
- Graceful shutdown and restart support

**Deliverable:** System runs unattended. You only receive emails when something genuinely needs your attention.

---

### Phase 5: Phone Agent — Outbound IVR (Weeks 3–4)
**Goal:** Handle outbound calls to buyers (e.g., Walgreens buyer lines) for order confirmation, status updates, or escalations that require a phone call.

- Built on Twilio (voice) + Vapi (AI voice agent) or ElevenLabs (TTS)
- IVR navigation: Agent calls, presses menu options, reaches the right department
- Scripted flows: "Calling to confirm PO #12345 received and processing" — waits for confirmation, logs outcome
- Transfer to operator: If call goes to voicemail or human wants to speak to someone, routes to Emmanuel's cell
- Use case: Walgreens has internal ordering systems that sometimes require phone confirmation. This eliminates that manual call.

**Deliverable:** Outbound confirmation call triggered by Manager Bot for orders above a configurable threshold value.

---

### Phase 6: Self-Improvement (Ongoing)
**Goal:** System gets better every week without additional development cost.

- Parser error log reviewed by Ollama weekly: patterns in failed extractions → prompt tuning
- A2000 rejection log: recurring validation errors → field mapping updates
- Invoice delivery failures: bounce tracking → contact list hygiene
- Monthly report to operator: throughput trends, error rate trend, time saved YTD
- OASIS AI quarterly review: assess new capabilities (new PO formats, new buyers, new integrations)

---

## A2000 Integration Options — Detailed

### Tier 1: REST API (Preferred)
GCS Software (A2000 vendor) offers a REST API for enterprise customers. If your licence includes API access, this is the cleanest path — no screen scraping, no DB risk.

- **Pros:** Officially supported, stable across A2000 updates, full CRUD on orders
- **Cons:** Requires GCS to enable and provide credentials — confirm during Phase 0
- **Endpoints needed:** Create order, get order status, retrieve invoice PDF

### Tier 2: EDI 850 Import (Reliable)
A2000 natively supports EDI (Electronic Data Interchange) — the industry standard for wholesale PO processing. We generate an EDI 850 file from the parsed PO and drop it into A2000's EDI import directory.

- **Pros:** Industry standard, A2000 supports it natively, battle-tested in wholesale
- **Cons:** Requires EDI mapping setup upfront, less real-time than API
- **Setup:** Map your trading partner IDs and segment definitions once — then runs automatically

### Tier 3: Direct Database Write (Risky — Fallback Only)
If A2000 exposes its Oracle or SQL Server database, we can write order records directly to the tables.

- **Pros:** No vendor dependency, maximum control
- **Cons:** Requires schema documentation, risk of data integrity issues, may void support contract
- **When to use:** Only if Tiers 1 and 2 are definitively unavailable

### Tier 4: Screen Automation (Always Available)
Playwright drives A2000's UI exactly as a human would — clicks, keyboard input, form navigation — but at machine speed with zero errors.

- **Pros:** Works on any A2000 version regardless of API access, no vendor coordination needed
- **Cons:** Brittle to A2000 UI updates, slower than API (2–5 seconds per field vs. instant)
- **When to use:** Development/demo mode, or as permanent fallback if other tiers fail

---

## Security Architecture

| Layer | Implementation |
|-------|---------------|
| LLM Processing | Ollama — runs 100% on your machine, no data sent to OpenAI or any cloud |
| Data Storage | SQLite with SQLCipher encryption at rest |
| Credentials | Stored in `.env` file, never committed to code, never logged |
| Network | Only outbound calls: Outlook (your own account) and A2000 (local network) |
| Audit Trail | Every agent action logged: timestamp, agent, action, result |
| Access Control | System runs under your Windows user account — no elevated privileges needed |
| Support Access | OASIS AI can remote-in ONLY with your explicit permission per session |

**Data never leaves your network for processing.** The only external calls are to services you already use (your own Outlook account, your own A2000 instance).

---

## Cost Estimate

### Development

| Phase | Hours | Rate (USD) | Cost |
|-------|-------|-----------|------|
| Phase 0: Discovery | 4 | — | Included |
| Phase 1: Email Agent | 12 | $150/hr | $1,800 |
| Phase 2: POS Integration | 16 | $150/hr | $2,400 |
| Phase 3: Invoice Loop | 8 | $150/hr | $1,200 |
| Phase 4: Manager Bot | 10 | $150/hr | $1,500 |
| **MVP Total** | **50 hrs** | | **$6,900** |
| Phase 5: Phone Agent (optional) | 20 | $150/hr | $3,000 |
| Phase 6 setup: Self-improvement | 6 | $150/hr | $900 |

### Infrastructure (Monthly)

| Component | Cost |
|-----------|------|
| Ollama (local LLM) | **$0** — runs on your hardware |
| SQLite | **$0** — open source |
| Cloud hosting | **$0** — runs on your machine |
| Twilio (if Phase 5) | ~$20–50/mo depending on call volume |
| **Total infrastructure** | **$0–50/mo** |

### Monthly Maintenance Retainer
Monitoring, error triage, prompt tuning, A2000 compatibility updates, quarterly review call.
**$300–500/mo** depending on order volume and complexity.

---

## Timeline

```
Week 1    Week 2    Week 3    Week 4    Ongoing
────────  ────────  ────────  ────────  ────────
[P0][P1]  [P2][P3]  [P4]──── [P5]────  [P6]────
Discovery  POS +     Manager   Phone     Self-
+ Email    Invoice   Bot       Agent     Improve
Agent      Loop      UAT       (opt.)
           ↑
         MVP LIVE
         (end week 2)
```

**2-week MVP:** Email → A2000 → Invoice → Email, fully automated, zero manual steps for routine orders.
**4-week production:** Manager Bot live, Phone Agent deployed (if in scope), Hermes running unattended.

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

**The headline number:** If you process 20 orders/day at 15 minutes each, that is 5 hours of daily manual work eliminated — every day, permanently.
