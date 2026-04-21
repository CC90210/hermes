---
mutability: SEMI-MUTABLE
tags: [hermes, brain, growth, evolution]
---

# GROWTH — Skill Evolution & Capability Protocol

> How Hermes grows new capabilities safely over time.
> New behaviors are proven before being trusted. Trust is earned through repetition.

## Core Principle: Compositionality

Complex workflows emerge from composing simple, proven skills. Before building anything new,
check whether it can be assembled from existing components.

```
Full PO Cycle = EmailAgent.poll_inbox + POParser.parse_and_persist + POSAgent.enter_order
              + POSAgent.retrieve_invoice + EmailAgent.send_invoice

Failure Recovery = list_orders_by_status(FAILED) + Orchestrator.handle_failures
                 + escalate(message) + audit_log(action)

Chargeback Prevention = EDI856ASN.generate + GS1Label.print + ChargebackTracker.track_window
                      + escalate_if_window_closing
```

When building a new skill, answer first: "Which existing skills does this compose?"

## Skill Lifecycle

```
DISCOVERY → IMPLEMENTATION → PROBATION → VALIDATED → (DEPRECATED)
```

| Stage | Definition | Gate to Next |
|-------|-----------|-------------|
| DISCOVERY | Need identified, not yet built | Decision to build |
| IMPLEMENTATION | Code written, tests passing | First successful real run |
| PROBATION [P] | Live but not fully trusted | 3 successful independent runs |
| VALIDATED [V] | Trusted for autonomous use | Sustained success or Emmanuel confirmation |
| DEPRECATED | Replaced by better approach | Noted in CHANGELOG.md, code kept |

## Probationary Validation Protocol

A skill starts as `[PROBATIONARY]` when:
- It's new (first time Hermes handles this order type or customer)
- It's reinstated after a failure
- It's a proposed change from `memory/PROPOSED_CHANGES.md` that was approved

**Promotion rules:**
- 3 successful independent runs → promote to `[VALIDATED]`
- 1 failure during probation → document in MISTAKES.md, do not auto-promote, reset count
- "Independent" means different orders, different days (not 3 orders in one cycle)

**Example:** When Walgreens EDI 856 ASN generation is first implemented, tag it `[PROBATIONARY]`.
After it runs successfully for 3 separate Walgreens shipments on 3 different days, promote to `[VALIDATED]`.

## Adding a New Skill — 4-Step Protocol

1. **Write SKILL.md** in `skills/[skill-name]/SKILL.md`. Include: purpose, inputs, outputs, failure modes.
2. **Implement** the CLI or adapter module. Add to `scripts/` or `adapters/`.
3. **Add tests** to `tests/`. At minimum: success path, failure path, idempotency check.
4. **Propose in PROPOSED_CHANGES.md** — list the skill, its lifecycle stage, and first planned use.

Only after Emmanuel (or CC during maintenance) reviews the proposal does the skill enter PROBATION.

## Capability Tiers

| Tier | Description | Example |
|------|------------|---------|
| 1 | Core pipeline | PO parsing, order entry, invoice delivery |
| 2 | Compliance automation | EDI 856 ASN, GS1-128 labels, EDI 855 ack |
| 3 | Financial intelligence | Contract pricing, credit checks, AR aging |
| 4 | Chargeback defense | 820 remittance reconciliation, dispute drafting |
| 5 | Expansion | Matrix expander, multi-buyer support |

## Capability Timeline

| Date | Tier | Capability | Status |
|------|------|------------|--------|
| 2026-04-18 | 1 | 5-stage PO→invoice pipeline | `[VALIDATED]` |
| 2026-04-18 | 1 | IMAP/SMTP email handling | `[VALIDATED]` |
| 2026-04-18 | 1 | PDF/Excel/EDI/text PO parsing (Ollama) | `[VALIDATED]` |
| 2026-04-18 | 1 | A2000 4-mode adapter ladder | `[VALIDATED]` |
| 2026-04-18 | 1 | SQLite audit log (append-only) | `[VALIDATED]` |
| 2026-04-18 | 1 | Warehouse PO PDF generation | `[VALIDATED]` |
| 2026-04-18 | 1 | Windows printer control (ZPL + PDF) | `[VALIDATED]` |
| 2026-04-18 | 2 | EDI 856 ASN generation | SKELETON (Phase 2b) |
| 2026-04-18 | 2 | GS1-128 carton label (ZPL) | SKELETON (Phase 2b) |
| 2026-04-18 | 3 | EDI 855 PO acknowledgment | SKELETON (Phase 3b) |
| 2026-04-18 | 3 | Contract price lookup | SKELETON (Phase 4b) |
| 2026-04-18 | 3 | Customer credit check | SKELETON (Phase 4b) |
| 2026-04-18 | 4 | Chargeback tracking + 28-day window | SKELETON (Phase 7b) |
| 2026-04-18 | 4 | EDI 820 remittance parser | SKELETON (Phase 6b) |
| 2026-04-18 | 5 | Apparel size-color matrix expander | SKELETON (Phase 5b) |

## Measuring Growth

Run this review monthly (or after any major deployment):

| Metric | Target | Notes |
|--------|--------|-------|
| Orders processed (last 30d) | > 0 | Baseline |
| Parse error rate | < 5% | Escalations / total POs |
| Failed orders (not recovered) | 0 | Every failure has a resolution |
| Chargebacks prevented | Count | EDI 856 + label compliance |
| New skills added | Count | Probationary or validated |
| Patterns promoted to VALIDATED | Count | From memory/PATTERNS.md |
| Escalations that required Emmanuel | Count | Lower = more capable Hermes |

## Governance

File mutability governs what Hermes can change on its own:

| File | Mutability | Change Process |
|------|-----------|---------------|
| brain/SOUL.md | IMMUTABLE | CC only, no queue |
| brain/HERMES.md | IMMUTABLE | CC only, no queue |
| brain/PRINCIPLES.md | SEMI-MUTABLE | PROPOSED_CHANGES.md → Emmanuel review |
| brain/BRAIN_LOOP.md | SEMI-MUTABLE | PROPOSED_CHANGES.md → Emmanuel review |
| brain/CAPABILITIES.md | GOVERNED | Update when capability changes, log in CHANGELOG.md |
| memory/PATTERNS.md | GOVERNED | Probationary → Validated through use |
| memory/CUSTOMERS.md | FREELY MUTABLE | Update from any session observation |
| brain/STATE.md | EPHEMERAL | Overwrite at session end |

## Obsidian Links
- [[brain/SOUL]] | [[brain/BRAIN_LOOP]] | [[brain/INTERACTION_PROTOCOL]]
- [[memory/PATTERNS]] | [[memory/MISTAKES]] | [[memory/PROPOSED_CHANGES]]
- [[brain/CAPABILITIES]] | [[brain/CHANGELOG]]
