---
mutability: EPHEMERAL
tags: [hermes, memory, tasks]
---

# Hermes — Active Tasks

> Updated after every material action.
> Statuses: OPEN | BLOCKED | DONE

## Open

_None currently._

## Blocked (Waiting on Emmanuel)

### DISC-001 — A2000 version and EDI module status
**Blocked on:** Emmanuel to confirm which A2000 version is installed and whether the EDI module is licensed.
**Why it matters:** Determines whether adapter mode is `api`, `edi`, or `playwright`. Affects Phase 2b (ASN generation).
**Asked:** 2026-04-18

### DISC-002 — Email stack confirmation
**Blocked on:** Emmanuel to confirm Outlook/Exchange hosting type and whether MFA is enabled.
**Why it matters:** If MFA is on, IMAP may be disabled and Microsoft Graph API will be required. Current implementation assumes IMAP.
**Asked:** 2026-04-18

### DISC-003 — Walgreens EDI requirements
**Blocked on:** Emmanuel to share Walgreens trading partner spec (ASN 856, label format, transmission window).
**Why it matters:** EDI compliance is the difference between zero chargebacks and $50K+/year in automatic fines.
**Asked:** 2026-04-18

### DISC-004 — Typical PO formats
**Blocked on:** Emmanuel to share sample POs (anonymized if needed) in each format received.
**Why it matters:** Parser validation needs real examples. Walgreens may use EDI 850 exclusively.
**Asked:** 2026-04-18

### DISC-005 — Number of Lowinger staff who will touch Hermes
**Blocked on:** Emmanuel to confirm headcount and roles.
**Why it matters:** Determines whether multi-user access controls are needed.
**Asked:** 2026-04-18

### DISC-006 — Claude API billing preference
**Blocked on:** Emmanuel to confirm: does Lowinger Distribution pay the Claude API bill directly, or is it baked into the OASIS retainer?
**Why it matters:** Required for invoice and billing setup.
**Asked:** 2026-04-18

## Done

### 2026-04-18 — v0.1.0 scaffold
Complete IDE layer scaffolded: CLAUDE.md, 8 CLI scripts, slash commands, brain files, memory placeholders, install.ps1. Tests: 36/36 passing.

### 2026-04-18 — v0.2.0 growth layer
SOUL.md, BRAIN_LOOP.md, GROWTH.md, INTERACTION_PROTOCOL.md, HEARTBEAT.md, CHANGELOG.md added.
Memory files seeded with real starter content. CLAUDE.md boot sequence updated. Tests: 215/215 passing.
