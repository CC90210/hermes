# Architecture Audit -- 2026-04-21

**Auditor:** Bravo (senior systems architect, OASIS AI)
**Scope:** Hermes v0.1.0, read-only review ahead of Emmanuel Lowinger deployment.
**Method:** Walked every file in adapters/, agents/, manager/, storage/, scripts/, brain/, skills/, clients/, docs/, tests/, plus top-level entry points. Traced every contract boundary.

## Summary

- Modules reviewed: 10 directories, 73 source files, 15 test files.
- Contract mismatches found: 6 (P0: 2, P1: 3, P2: 1)
- Orphan code identified: 3 files / ~100 lines plus 4 one-line shim files.
- Doc-code drift: 7 instances
- Overall: DRIFT -- not broken, ships as-is against the mock A2000, but 2 P0 issues surface the first time a real PO runs through retrieve_invoice or enter_order against anything other than the in-memory mock.

The strengths are real: clean A2000ClientBase adapter pattern, honest NotImplementedError stubs, surgical audit logging, disciplined async/SQLite. The drift is concentrated at the POData<->DB boundary and in the brain/skills/docs layer that was scaffolded faster than the code.

---

## Findings by category

### Contract drift

**[P0] POData <-> orders table schema mismatch.**
POData (adapters/po_parser.py:75-88) declares 6 fields that do not exist as columns on the orders table (storage/db.py:40-50): customer_address, ship_to_address, order_date, ship_date, notes, raw_text. POData.from_db_row(), POSAgent.enter_order() (pos_agent.py:63-83), and Orchestrator._process_order() (orchestrator.py:212-232) all call row.get(customer_address), row.get(ship_to_address), etc. -- these silently return None because the columns do not exist.

Consequences:
- EDIA2000Client._build_x12_850() (a2000_client.py:209-221) branches on po.customer_address; in production the entire bill-to address block is always skipped. EDI 850 output is missing N3/N4 segments.
- warehouse_po_pdf.generate_warehouse_po() receives a POData with customer_name populated (that column exists) but blank address. Warehouse slip prints the customer but no ship-to.
- POParser.parse_and_persist() extracts these 6 fields via Ollama and then throws them away on insert. The LLM work is wasted every cycle.

Fix direction: either (a) extend the orders schema with those columns and update create_order() + pos_agent.enter_order(), or (b) persist the extracted POData JSON into a new raw_extraction_json column and rehydrate from it. Option (a) is closer to the DB is source of truth principle in brain/PRINCIPLES.md section 6.


**[P0] POSAgent.retrieve_invoice calls the wrong adapter contract.**
POSAgent.retrieve_invoice(order_id, a2000_client) (pos_agent.py:115-141) passes str(order_id) to a2000_client.get_invoice(). The order_id coming in is the internal SQLite row id (an int like 42). But MockA2000Client.get_invoice() (a2000_client.py:102-111) looks up self._orders[order_id] where keys are A2000-assigned strings like MOCK-069E55CA -- the id returned by create_order(). These two namespaces are never reconciled. The mock tests pass only because test_a2000_mock.py creates an order and immediately reuses the returned A2000 ID in-process. In the real pipeline, enter_order() does NOT capture the OrderResult.order_id from a2000_client.create_order(po) (line 105: return value is discarded) and does NOT store it on the orders row. Then retrieve_invoice passes the SQLite row id, which the A2000 client has never heard of. KeyError at runtime.

Fix direction: add a2000_order_id TEXT and a2000_invoice_number TEXT columns to orders, have enter_order() capture OrderResult and persist it, have retrieve_invoice() read the A2000 id from the DB before calling get_invoice().

**[P1] Orchestrator imports four adapter shims that exist only to rename the same classes.**
manager/orchestrator.py:54-67 imports A2000MockClient, A2000ApiClient, A2000EdiClient, A2000PlaywrightClient from adapters/a2000_mock.py, a2000_api.py, a2000_edi.py, a2000_playwright.py -- each is a 4-line shim re-exporting the real classes from adapters/a2000_client.py under a different name. Meanwhile adapters/a2000_client.py:319-339 defines get_a2000_client() which already maps modes to classes correctly and is what tests use. The orchestrator rebuilds this factory by hand. There are now two factories (_build_a2000_client in orchestrator, get_a2000_client in adapters) and four trivial shim files whose only purpose is to reconcile a naming inconsistency (MockA2000Client vs A2000MockClient). Pick one name, delete the other four files, delete _build_a2000_client, use get_a2000_client(config.a2000_mode).

**[P1] EmailAgent.poll_inbox body decoding ignores declared charset.**
poll_inbox (email_agent.py:106-179) decodes every text/plain part with utf-8, errors=replace and never honors the part declared charset. ASCII/UTF-8 POs are fine; a Walgreens PO sent as iso-8859-1 or windows-1252 (common from legacy EDI gateways) will have mangled non-ASCII characters fed into the Ollama prompt. Use part.get_content_charset() and fall back to utf-8.

**[P1] raw_email_id uniqueness is not enforced.**
PRINCIPLES.md section 2 Idempotent by Design claims UID tracking prevents duplicate orders. storage/db.py:40-50 does NOT declare raw_email_id UNIQUE, and create_order() does not check for existing rows before insert. If IMAP returns the same UID twice (reconnect races, folder reselect, message move), duplicate orders are created. Add a partial unique index on orders(raw_email_id) WHERE raw_email_id IS NOT NULL and have create_order() catch IntegrityError and return the existing row id.

**[P2] _extract_text_edi element/segment separator detection reads fixed offsets.**
po_parser.py:153-155: element_sep = raw[3], segment_sep = raw[105]. The ISA envelope is 106 bytes -- offset 105 is the segment terminator only when the envelope has exactly the expected layout. If there is leading whitespace (many VANs prepend CRLF or BOMs) both offsets are wrong. Read the ISA explicitly: isa_start = raw.find(ISA), then raw[isa_start+3], etc.

### Orphan code

1. **agents/phone_agent.py** -- 74 lines. All three methods raise NotImplementedError. Nothing imports it: grep across the repo shows only AGENTS.md and CAPABILITIES.md references. Orchestrator does not instantiate it. Tests do not exist. brain/AGENTS.md PhoneAgent entry marks it Phase 2 (stub). If Phase 2 is 3+ months away, move this file to docs/future/phone_agent_stub.py or delete it and let git history hold the scaffold.

2. **AGENTS.md (root, 15 lines)** -- duplicates information now in brain/AGENTS.md. The only reason it exists is the Cursor/Windsurf convention of reading AGENTS.md from the repo root. Either delete (CLAUDE.md is the canonical entry point) or add name/description frontmatter.

3. **cron/scheduler.py plus main.py duplication.** main.py is a 57-line wrapper that prints a banner then calls cron.scheduler.main(). cron/scheduler.py is the real CLI. Collapse cron/scheduler.py into main.py and delete the cron/ directory.

4. **demo/demo_with_ollama.py** -- 9,841 bytes, parallel to demo/run_demo.py. README only documents demo.run_demo. Nothing calls demo_with_ollama.py. Delete or fold into run_demo.py.

### Doc-code drift

1. **README.md:94** claims 141 automated tests currently pass. The audit request header says 173 tests pass. Update README or point it at make test so the number stays current.

2. **README.md:97** says 11 CLI tools. scripts/ has 12 tool scripts (chargeback_tool, customer_tool, email_tool, health_tool, invoice_tool, po_tool, pos_tool, printer_tool, quote_tool, report_tool, system_tool) plus setup_db.py and state_sync.py. Pick a count and sync it.

3. **README.md:98** says 8 slash commands. .claude/commands/ has 9 files (chargebacks, customer, daily-briefing, draft-email, print, process-pending, quote, re-run-order, status). brain/QUICK_REFERENCE.md also lists 8. Off-by-one.

4. **README.md:184-189 folder layout** no mention that po_parser.py lives in adapters/ despite being architecturally an agent.

5. **brain/CAPABILITIES.md:155-165 Auto-print wiring** HERMES_PRINT_LABELS=1 is documented but not wired; GS1-128 label adapter is live code (443 lines, tested) but no orchestrator wiring.

6. **brain/ARCHITECTURE.md:14-27 system diagram** omits scripts/ entirely -- majority of Hermes surface area (scripts/ = 2,534 LOC vs manager/ = 517 LOC). Add an IDE-layer box.

7. **docs/BUILD_PLAN.md:187** says 10 commits of real implementation -- stale.

### Naming inconsistencies

- **Adapter class names:** MockA2000Client (internal, a2000_client.py) vs A2000MockClient (orchestrator expectation, shim file). Four shim files exist to bridge this. Same for APIA2000Client/A2000ApiClient, EDIA2000Client/A2000EdiClient, PlaywrightA2000Client/A2000PlaywrightClient. Pick one naming style and unify.
- **buyer_name vs customer_name:** Consistent on customer_name in POData, orders table, and all storage calls. matrix_expander.py:50-74 correctly uses buyer_code/vendor_sku for SKU cross-reference -- semantically distinct. No action needed.
- **ide-hermes vs pipeline agent_name in audit_log:** scripts/pos_tool.py:72 and scripts/invoice_tool.py:80 write agent_name=ide-hermes with details.source=ide. Pipeline agents write no source key. CLAUDE.md Rule 7 enforced in only 2 of 11 scripts. The 60-second collision-detection mechanism in docs/IDE_HERMES_DESIGN.md:245 is therefore unimplemented.
- **Invoice number path:** pos_agent.retrieve_invoice uses invoice_path.stem as invoice number (orchestrator.py:286). But MockA2000Client.create_order returns OrderResult with invoice_number=INV-xxxxxx that is never persisted. Real invoice number is lost.

### Missing glue

1. **No a2000_order_id / invoice_number columns on orders.** See contract drift P0 number 2.

2. **No source column on audit_log** despite docs/IDE_HERMES_DESIGN.md:245 design requirement. Add source TEXT NOT NULL DEFAULT pipeline to the DDL and populate it explicitly.

3. **No chargeback persistence.** adapters/chargeback_tracker.py is a 160-line skeleton. scripts/chargeback_tool.py:33 stores them in storage/chargebacks.json. The DB has no chargebacks table. JSON sidecar will drift from audit_log and is not durable against concurrent IDE + pipeline write.

4. **Compliance stack is code without callers.** edi_855_ack.py (343 LOC), edi_856_asn.py (476 LOC), edi_820_remit.py (307 LOC), gs1_128_label.py (443 LOC), chargeback_tracker.py (160 LOC), contract_price.py (174 LOC), credit_check.py (98 LOC), matrix_expander.py (313 LOC) -- 2,314 lines of real implementation, zero calls from manager/orchestrator.py. Add a Phase 2b wiring point marker in orchestrator.py:_process_order.

5. **HERMES_PO_DROP_FOLDER env var declared but not implemented.** .env.template:67-68 promises a folder watcher fallback. system_tool.py has --watch. Nothing ties them together in the orchestrator.

6. **escalation_email with no validation.** config.escalation_email defaults to empty string. If Emmanuel forgets to set it, escalate() SMTPs to empty string and fails silently. Validate at startup: if A2000_MODE is not mock, ESCALATION_EMAIL must be non-empty.

7. **HEALTH_PORT=8765 mentioned in health_tool.py** but no HTTP health endpoint exists. docs/IDE_HERMES_DESIGN.md:243 plans for curl localhost:8765/health. Nothing serves on that port. Either serve it or remove the design reference.

### Architectural strengths (keep doing this)

1. **Adapter pattern on A2000ClientBase is clean.** Four modes, one ABC, explicit NotImplementedError. get_a2000_client() factory in one place. Swapping modes is a single env var change. Textbook.

2. **SQLite-as-source-of-truth discipline.** POSAgent.enter_order re-reads from DB instead of accepting POData -- principle 6 enforced in code. Right call even though it means the POData vs DB drift (P0 number 1) is a real cost.

3. **Audit log is uniformly append-only.** Every state-changing path in the pipeline calls log_audit. No UPDATE/DELETE on audit_log anywhere. IDE scripts are the weak link, not the pipeline.

4. **Config validation at import time.** manager/config.py:19-24 raises at module load if required env vars are missing. Mode-specific validation at _validated_a2000_mode (config.py:72-91). A whole class of why-wont-Hermes-start bugs never materializes.

5. **Failure handling is honest.** handle_failures uses a retry counter, not clock ticks. Escalations deduplicated by scanning audit_log. _MAX_RETRIES = 3 is named, not magical.

6. **Windows-aware.** run_forever handles signal registration on Windows where add_signal_handler does not work (orchestrator.py:479-484). Rare to see this handled on first pass.

7. **Tests at the right layer.** Tests exercise orchestrator state machine, config validation, DB schema, and adapter contracts -- not internal helpers. test_orchestrator_failures.py tests the retry/escalation path end-to-end against a real temp SQLite. Right testing discipline for a 0.1.0 going to a paying client.

---

## Recommendations (prioritized)

1. **[P0, this week, ~1h Bravo]** Fix POData vs orders schema drift. Extend DDL with customer_address, ship_to_address, order_date, ship_date, notes, raw_text columns. Update create_order() signature to accept them. Rerun tests. Unblocks real EDI 850 output and real warehouse slips.

2. **[P0, this week, ~45min Bravo]** Persist A2000 order id and invoice number. Add a2000_order_id, invoice_number columns to orders. Capture OrderResult in pos_agent.enter_order() and write both fields. Rewrite pos_agent.retrieve_invoice() to read a2000_order_id from DB before calling get_invoice().

3. **[P1, this week, ~30min Bravo]** Delete the 4 shim files in adapters/a2000_mock/_api/_edi/_playwright.py and the _build_a2000_client function. Rename classes in a2000_client.py to A2000MockClient / A2000ApiClient / etc. Use get_a2000_client() everywhere. Net removal: ~30 LOC.

4. **[P1, next week, ~1h Bravo]** Add source TEXT NOT NULL DEFAULT pipeline column to audit_log. Update log_audit() signature. Update all 11 script call sites to pass source=ide. Wire the 60-second cooldown check in IDE scripts.

5. **[P1, next week, ~45min Bravo]** Enforce raw_email_id uniqueness at the DB level. Add partial unique index; handle IntegrityError in create_order() by returning the existing row id.

6. **[P2, before Walgreens phase 2b]** Wire gs1_128_label and edi_856_asn into the orchestrator. Add explicit integration tests. The compliance stack is the number-one ROI argument -- leaving it unwired turns a Walgreens-ready story on its head.

7. **[Cleanup, 20min]** Sync doc numbers: 173 tests, 12 scripts, 9 slash commands. Delete root AGENTS.md stub (CLAUDE.md is canonical). Delete or fold in demo/demo_with_ollama.py. Decide on phone_agent.py: move to docs/future/ or keep with a Phase 2 tag.

8. **[Hardening, 30min]** Honor charset in EmailAgent.poll_inbox. Robust ISA separator detection in _extract_text_edi. Validate ESCALATION_EMAIL non-empty when A2000_MODE is not mock.

**Net effort to ship-clean for Emmanuel:** ~5 hours Bravo / ~1.5 days human team.

**Completeness of fixed system:** 9/10. The 1 point held back is the compliance stack -- live code, not yet called. That is explicitly Phase 2b, not v0.1.0.
