---
mutability: GOVERNED
tags: [hermes, memory, patterns, learning]
---

# Hermes — Validated Patterns

> [P] = probationary (used successfully 1–2 times — not yet trusted for full autonomy)
> [V] = validated (3+ successful independent uses — trusted for autonomous execution)
>
> Every [P] pattern tracks its use count. At 3: promote to [V] and log in CHANGELOG.md.

---

### [V] 4-Mode A2000 Adapter Ladder
**Pattern:** Select the A2000 adapter by escalating capability: mock (dev) → api (REST, if available)
→ edi (X12 850 file, if EDI module licensed) → playwright (browser automation, fallback).
**When to apply:** Every time A2000 connectivity is configured or changed.
**Validated:** Architecture design (3 independent design reviews confirmed this is the right structure).
**Composites:** A2000ClientBase + config.A2000_MODE env var + Orchestrator._build_a2000_client()

---

### [V] Mutability-Tier Governance for Self-Modification
**Pattern:** Before changing any brain/ or memory/ file, check its mutability tier.
IMMUTABLE → stop. SEMI-MUTABLE → write to PROPOSED_CHANGES.md and wait. GOVERNED → update + log
in CHANGELOG.md. FREELY MUTABLE / EPHEMERAL → update directly.
**When to apply:** Every proposed change to any governance file.
**Validated:** Adopted from Bravo V5.5 architecture, validated across 3+ agent deployments.
**Composites:** INTERACTION_PROTOCOL.md Section 2 + PROPOSED_CHANGES.md + CHANGELOG.md

---

### [V] Audit-Log-Everything for Commerce Operations
**Pattern:** Call log_audit() BEFORE the external action (intent logged) AND after (outcome logged).
Never let an external state change happen without an audit entry. If audit writing fails, do not
proceed with the action.
**When to apply:** Every A2000 interaction, every email sent, every order status change.
**Validated:** Core to PRINCIPLES.md #4. Proven across all pipeline stages.
**Composites:** storage.db.log_audit() + PRINCIPLES.md #4 + ARCHITECTURE.md Audit Log Contract

---

### [P] IDE/Daemon Boundary Check Before Acting (used: 1)
**Pattern:** Before taking any state-changing action in IDE mode, check `orders.status` in the DB
and log `source: "ide"` in the audit entry. This prevents collision with the background daemon which
may be running the same cycle simultaneously.
**When to apply:** Any IDE-triggered order action (re-run, manual process, etc.)
**First use:** 2026-04-18 (architectural lesson from build session)
**Use count:** 1 / 3

---

### [P] Capabilities Must Match Code, Not Aspirations (used: 1)
**Pattern:** Never describe a capability in README, CAPABILITIES.md, or brain files without a
corresponding test or code path. Forward-looking items are labeled "Phase N (not yet implemented)"
explicitly. Check by running `python -m pytest tests/ -q` after writing any new capability claim.
**When to apply:** Before any documentation update that adds a new capability description.
**First use:** 2026-04-18 (lesson from voice capability description without implementation)
**Use count:** 1 / 3

---

## Anti-Patterns

- Never enter an order without checking `orders.status` first (idempotency violation)
- Never send an invoice email if `retrieve_invoice()` returned None (fail-open violation)
- Never escalate with a vague "something went wrong" — always include PO number + specific question
- Never modify audit_log rows — it is append-only

*Last updated: 2026-04-18*

## Obsidian Links
- [[brain/BRAIN_LOOP]] | [[memory/MISTAKES]] | [[memory/SELF_REFLECTIONS]]
- [[brain/GROWTH]] | [[brain/PRINCIPLES]]
