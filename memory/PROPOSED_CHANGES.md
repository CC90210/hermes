---
mutability: EPHEMERAL
tags: [hermes, memory, governance, proposals]
---

# PROPOSED CHANGES — Self-Modification Queue

> Hermes writes proposals here for SEMI-MUTABLE file changes.
> Emmanuel or CC reviews and approves or rejects before Hermes applies anything.
> Clear entries here after they are APPLIED or REJECTED (move to Applied History below).

## Format

```
## YYYY-MM-DD — Proposed: [title]
**File(s) affected:** brain/PRINCIPLES.md
**Rationale:** [Why this change improves operations]
**Proposed change:** [Exact text to add/change/remove]
**Risk:** [What could go wrong if this is applied incorrectly]
**Rollback:** [How to undo — git revert or specific edit]
**Status:** PENDING_REVIEW | APPROVED | REJECTED | APPLIED
```

---

## Active Proposals

### 2026-04-18 — Proposed: Add EDI 856 ASN dispatch rule to PRINCIPLES.md
**File(s) affected:** `brain/PRINCIPLES.md`
**Rationale:** Once the EDI 856 ASN generation is live (Phase 2b), Hermes needs an explicit
rule about when to dispatch the ASN relative to order entry — Walgreens requires it BEFORE
shipment, not after. This is a compliance-critical operating principle.
**Proposed change:** Add a 7th principle: "7. ASN-First. For EDI-compliant buyers, generate
and send the EDI 856 ASN before the shipment departs. Never ship first and send the ASN after."
**Risk:** Low. This is an additive principle, not a change to existing ones.
**Rollback:** Remove the added section from PRINCIPLES.md.
**Status:** PENDING_REVIEW

---

### 2026-04-18 — Proposed: Add Microsoft Graph API path to CAPABILITIES.md and email routing
**File(s) affected:** `brain/CAPABILITIES.md`, `CLAUDE.md`
**Rationale:** If Emmanuel's Outlook uses Microsoft 365 with MFA, IMAP may be disabled and
Graph API will be required. The current routing assumes IMAP. This change adds a conditional
note so Hermes knows to check before connecting.
**Proposed change:** Add a "Not yet capable" row under Email Operations: "Microsoft Graph API /
OAuth 2.0 (current: IMAP/SMTP only)". Add to CLAUDE.md Rule 2: note that email_tool.py assumes
IMAP; if IMAP fails, check EMMANUEL.md for Graph API credentials.
**Risk:** Low. Discovery change only — does not affect current behavior.
**Rollback:** Remove the added note.
**Status:** PENDING_REVIEW

---

## Applied History

*Entries are moved here after APPLIED or REJECTED status.*

*No history yet.*

---

## Obsidian Links
- [[brain/INTERACTION_PROTOCOL]] | [[brain/CHANGELOG]] | [[brain/PRINCIPLES]]
- [[memory/DECISIONS]] | [[memory/SESSION_LOG]]
