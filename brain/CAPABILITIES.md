---
tags: [hermes, brain]
---

# CAPABILITIES — What Hermes Can Do

> Current capability registry, organized by domain. Verified against the codebase.
> "Not yet" items are planned but not implemented.

## Email Operations

| Capability | Method | Notes |
|-----------|--------|-------|
| Poll inbox for UNSEEN messages | `EmailAgent.poll_inbox()` | IMAP UID-based, returns raw dicts |
| Detect PO by subject tokens | `_looks_like_po_subject()` | Tokens: "po", "purchase order", "order #", "order#" |
| Detect PO by attachment filename | `_looks_like_po_attachment()` | Extensions: .pdf, .xlsx, .xls, .csv |
| Send invoice as email attachment | `EmailAgent.send_invoice()` | SMTP with TLS, logs to audit_log |
| Send HTML alert/escalation email | `EmailAgent.send_alert()` | Used by Orchestrator for operator alerts |
| Check IMAP connection alive | `EmailAgent.is_connected()` | Returns bool; used by health check |

**Not yet capable:**
- Microsoft Graph API / OAuth 2.0 (current: IMAP/SMTP only)
- Parsing email thread history (processes latest message only)
- Bounce detection

## POS Operations (A2000)

| Capability | Method | Modes |
|-----------|--------|-------|
| Create order in A2000 | `A2000ClientBase.create_order(po)` | mock, api*, edi, playwright* |
| Retrieve order details | `A2000ClientBase.get_order(id)` | mock only (api/edi/playwright: NotImplemented) |
| Fetch invoice PDF bytes | `A2000ClientBase.get_invoice(id)` | mock only (edi: returns 810 inbound) |
| Send print command | `A2000ClientBase.print_order(id)` | mock only |
| Validate connection on startup | `A2000ClientBase.validate()` | all modes (no-op for mock) |
| Check reachability | `A2000ClientBase.is_reachable()` | all modes (returns True for mock) |
| Write EDI X12 850 file to disk | `EDIA2000Client.create_order()` | edi mode |
| Build full ISA/GS/ST/BEG/PO1/CTT envelope | `_build_x12_850()` | edi mode |

*api: stubs only, awaiting vendor credentials. playwright: structure only, selectors TBD.

## Parser Operations

| Capability | Function | Notes |
|-----------|----------|-------|
| Extract text from PDF | `_extract_text_pdf()` | Uses pdfplumber, multi-page |
| Extract text from Excel (.xlsx/.xls) | `_extract_text_excel()` | openpyxl, all sheets, read-only |
| Extract structured data from EDI X12 850 | `_extract_text_edi()` | Parses BEG, N1, N3, N4, PO1, CTT segments |
| Strip HTML tags for email body | `_extract_text_html()` | Regex-based, handles encoded entities |
| Send extracted text to Ollama | `_call_ollama()` | model=qwen2.5:32b, temperature=0, format=json |
| Build POData from LLM response | `_build_po_data()` | Validates types; defaults qty=0, price=0.0 |
| Parse PO from raw bytes (public API) | `parse_po(content, filename, content_type)` | Format auto-detected |
| Parse + persist from raw email dict | `POParser.parse_and_persist()` | Creates orders + order_lines rows |
| Validate POData fields | `validate_po(po)` | Returns list of human-readable errors |

**Not yet capable:**
- EDI 997 Functional Acknowledgement (inbound)
- CSV format with custom column mapping
- Multi-attachment emails (processes first PO attachment only)

## Storage Operations

| Capability | Function | Notes |
|-----------|----------|-------|
| Initialize database schema | `init_db(db_path)` | Idempotent, WAL mode, foreign keys on |
| Create order row | `create_order(...)` | Returns order_id (int) |
| Create order line row | `create_order_line(...)` | Linked to order_id |
| Get order by id | `get_order(db_path, order_id)` | Returns dict or None |
| Get order lines | `get_order_lines(db_path, order_id)` | Returns list of dicts |
| Update order status | `update_order_status(...)` | Valid statuses: OrderStatus enum |
| List orders by status | `list_orders_by_status(...)` | Used for failure recovery |
| Append audit log entry | `log_audit(...)` | Append-only, JSON details |
| Get audit log (filtered by agent) | `get_audit_log(...)` | Used by failure handler |

## Orchestration

| Capability | Method | Notes |
|-----------|--------|-------|
| Full 5-stage cycle | `Orchestrator.run_cycle()` | Returns {processed, failed, skipped} |
| Recover stalled orders | `_resume_stalled_orders()` | Re-queues PARSED and ENTERED orders |
| Retry or escalate failures | `handle_failures()` | 3 strikes → escalate |
| Health check | `health_check()` | Returns dict (see ARCHITECTURE.md) |
| Escalate to operator | `escalate(message)` | Sends HTML email to ESCALATION_EMAIL |
| Run forever on interval | `run_forever(interval_seconds)` | Default 300s, SIGINT-safe |
| Select A2000 client by mode | `_build_a2000_client(mode)` | Reads A2000_MODE env var |

## Not Yet Capable (Phase 2+)

- **PhoneAgent** — IVR navigation via Twilio/Vapi (skeleton exists in `agents/phone_agent.py`)
- **EDI 997** — Functional acknowledgement for inbound EDI
- **Real-time WebSocket push** — Current model is polling; no push channel
- **Dashboard UI** — No web interface; status exposed only via `--health` flag
- **Multi-client routing** — One process per client; no shared orchestrator

---

## Phase 2b+ — In Design (Compliance Stack)

Scaffolded in this pass. No implementation yet — all methods raise NotImplementedError.
See `docs/BUILD_PLAN.md` for phase definitions and timelines.

| Capability | Module | Phase Tag | Status |
|-----------|--------|-----------|--------|
| EDI 855 PO Acknowledgment (accept / change / reject) | `adapters/edi_855_ack.py` | Phase 3b | Skeleton |
| EDI 856 Advance Ship Notice generator | `adapters/edi_856_asn.py` | Phase 2b | Skeleton |
| ASNBuilder hierarchical HL-loop structure | `adapters/edi_856_asn.py` | Phase 2b | Skeleton |
| CartonContent dataclass (SSCC, GTIN, qty) | `adapters/edi_856_asn.py` | Phase 2b | Skeleton |
| EDI 820 Remittance Advice parser | `adapters/edi_820_remit.py` | Phase 6b | Skeleton |
| RemittanceAdvice + Deduction dataclasses | `adapters/edi_820_remit.py` | Phase 6b | Skeleton |
| GS1-128 carton label — ZPL output (Zebra) | `adapters/gs1_128_label.py` | Phase 2b | Skeleton |
| GS1-128 carton label — PDF fallback | `adapters/gs1_128_label.py` | Phase 2b | Skeleton |
| SSCC-18 compute with Modulo-10 check digit | `adapters/gs1_128_label.py` | Phase 2b | Skeleton |
| Apparel size-color matrix detection | `adapters/matrix_expander.py` | Phase 5b | Skeleton |
| Matrix → flat line-item expansion | `adapters/matrix_expander.py` | Phase 5b | Skeleton |
| Buyer item code ↔ vendor SKU cross-reference | `adapters/matrix_expander.py` | Phase 5b | Skeleton |
| Contract price lookup (volume tiers, promo windows) | `adapters/contract_price.py` | Phase 4b | Skeleton |
| PO pricing validation against A2000 table | `adapters/contract_price.py` | Phase 4b | Skeleton |
| Customer credit hold check | `adapters/credit_check.py` | Phase 4b | Skeleton |
| CreditCheckResult (approve / hold / escalate) | `adapters/credit_check.py` | Phase 4b | Skeleton |
| Chargeback deduction tracking (28-day window) | `adapters/chargeback_tracker.py` | Phase 7b | Skeleton |
| Dispute window countdown + escalation alerts | `adapters/chargeback_tracker.py` | Phase 7b | Skeleton |
| Auto-draft dispute submission email | `adapters/chargeback_tracker.py` | Phase 7b | Skeleton |

## Obsidian Links
- [[brain/HERMES]] | [[brain/ARCHITECTURE]] | [[brain/AGENTS]]
