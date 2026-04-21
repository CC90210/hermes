---
mutability: GOVERNED
tags: [hermes, memory, persistent, long-term]
---

# LONG-TERM MEMORY — Persistent Facts

> Facts that survive session resets. Only include facts with confidence >= 0.8.
> Add new facts freely. Review quarterly — demote or remove stale facts.
> Source everything: where did this fact come from?

## Client: Lowinger Distribution

| Fact | Confidence | Source | Last Verified |
|------|-----------|--------|---------------|
| Client name: Lowinger Distribution | 1.0 | Emmanuel confirmed | 2026-04-18 |
| Operator: Emmanuel Lowinger | 1.0 | Client contract | 2026-04-18 |
| Primary buyer: Walgreens | 0.95 | EMMANUEL.md, context | 2026-04-18 |
| Invoice billing name: "Lowinger Distribution" | 0.95 | CC stated during build | 2026-04-18 |
| POS system: A2000 (GCS Software apparel/fashion ERP) | 0.90 | ARCHITECTURE.md, CC context | 2026-04-18 |
| A2000 version: TBD — discovery question open | 0.5 | EMMANUEL.md open questions | 2026-04-18 |
| Email stack: Outlook / Microsoft 365 (IMAP vs Graph API TBD) | 0.6 | EMMANUEL.md open questions | 2026-04-18 |
| Order volume estimate: 10–50 POs/day | 0.5 | EMMANUEL.md estimate | 2026-04-18 |
| Introduced by: Adon (PropFlow partner) | 0.95 | EMMANUEL.md | 2026-04-18 |

## Domain: Wholesale Commerce

| Fact | Confidence | Source | Last Verified |
|------|-----------|--------|---------------|
| Walgreens Cost Recovery Program: automatic chargebacks for non-compliance | 0.95 | HERMES.md context | 2026-04-18 |
| Walgreens chargeback exposure: $50K–$150K/year if compliance stack absent | 0.85 | HERMES.md context | 2026-04-18 |
| EDI 856 ASN must be sent BEFORE shipment (Walgreens requirement) | 0.95 | Domain knowledge | 2026-04-18 |
| Chargeback dispute window: 28 days from deduction (standard) | 0.85 | Domain knowledge | 2026-04-18 |
| Walgreens DSD vs DC routing TBD — discovery question open | 0.4 | CUSTOMERS.md note | 2026-04-18 |

## System Architecture

| Fact | Confidence | Source | Last Verified |
|------|-----------|--------|---------------|
| Hermes runs LOCAL only — no cloud AI in the pipeline | 1.0 | SOUL.md, PRINCIPLES.md | 2026-04-18 |
| SQLite is the single source of truth — all state lives in the DB | 1.0 | PRINCIPLES.md | 2026-04-18 |
| Ollama (local) handles PO extraction — model: qwen2.5:32b, temperature=0 | 0.95 | CAPABILITIES.md | 2026-04-18 |
| Claude API is only used for the IDE chat interface (CLAUDE.md) | 0.95 | Architecture decision | 2026-04-18 |
| A2000_MODE env var selects the adapter: mock | api | edi | playwright | 0.95 | ARCHITECTURE.md | 2026-04-18 |
| Audit log is append-only — no UPDATE or DELETE ever | 1.0 | PRINCIPLES.md | 2026-04-18 |
| Max retries before escalation: 3 (Orchestrator._MAX_RETRIES) | 0.95 | PRINCIPLES.md, code | 2026-04-18 |

## Commerce Domain: What Hermes Does NOT Do

| Boundary | Confidence | Notes |
|----------|-----------|-------|
| No pricing decisions | 1.0 | Pricing is Emmanuel's domain |
| No credit limit adjustments | 1.0 | Credit decisions require human judgment |
| No order cancellations without confirmation | 1.0 | Irreversible — always escalate |
| No outbound sales or customer acquisition | 1.0 | Hermes handles incoming orders only |
| No business strategy advice | 1.0 | Operational execution only |

## Creator

| Fact | Confidence | Source |
|------|-----------|--------|
| Created by: OASIS AI Solutions (Conaugh McKenna) | 1.0 | SOUL.md |
| CC manages Hermes codebase and governance | 1.0 | CLAUDE.md |
| Emmanuel is the operator for this deployment | 1.0 | EMMANUEL.md |

## Obsidian Links
- [[brain/SOUL]] | [[brain/EMMANUEL]] | [[memory/CUSTOMERS]] | [[memory/DECISIONS]]
