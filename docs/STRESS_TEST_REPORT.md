# Stress Test Report — 2026-04-18

## Executive Summary
- Test suite: 173/173 passes across 5 runs (1 skipped, deterministic)
- Demo: 20/20 successful runs — all order IDs unique (UUID4-based)
- Linter findings: 28 ruff errors (all F-class: unused imports, dead vars, f-string nits), 11 mypy errors (1 real API mismatch + 10 None-unchecked attribute accesses)
- Adversarial tests: size-guard OK, path-traversal OK, delimiter-strip OK, zero-pallets OK, 500-carton OK, concurrent DB OK — 2 logic bugs found in EDI hierarchy and matrix detection
- **Overall: DEGRADED** — 2 production-level bugs found

---

## Findings (by severity)

### P0 — Immediate production blocker

**EDI 856 HL hierarchy is wrong for any shipment with >1 carton or >1 pallet**

File: `adapters/edi_856_asn.py` lines 252, 258.

The tare and pack HL callers pass `hl_counter - 1` as `parent_id`. Because `hl_counter` is incremented inside each `_build_*_hl` call before returning, the value of `hl_counter - 1` at the call site is the ID of the *last-built segment*, not the correct hierarchical parent. Even the single-pallet case is wrong: Tare reports parent=1 (Shipment) instead of parent=2 (Order).

Observed 2-pallet output:
```
HL id=3 parent=1 type=T  (should be parent=2/Order)
HL id=4 parent=2 type=P  (should be parent=3/Tare)
HL id=6 parent=4 type=P  (should be parent=3/Tare, not Pack)
HL id=8 parent=6 type=T  (should be parent=2/Order, not Pack)
```

Walgreens EDI validation rejects ASNs with incorrect HL parent IDs. Every shipment with more than one carton per pallet will be auto-rejected, generating a compliance chargeback. The three dead variables `order_hl_id`, `tare_hl_id`, `pack_hl_id` (flagged by ruff F841) were intended to track correct parents but were never wired in.

Fix: replace `hl_counter - 1` with the saved ID variables — they already exist.

---

### P1 — Will cause issues in first month

**`orchestrator.setup()` always attempts a live IMAP connection — no mock path**

File: `manager/orchestrator.py` line 98, `agents/email_agent.py` line 66.

`EMAIL_BACKEND=mock` is in config but `EmailAgent.connect()` ignores it and calls imapclient unconditionally. There is no way to run the full orchestrator lifecycle without live IMAP credentials. Any CI pipeline or dev machine without email access will fail at setup.

**`APIA2000Client` constructor does not accept `api_url` / `api_key` args**

File: `manager/orchestrator.py` line 58, `adapters/a2000_client.py` line 133.

mypy confirms: `Unexpected keyword argument "api_url" for "APIA2000Client"`. The client reads credentials from env directly; the orchestrator passes them as kwargs anyway. Latent bug — harmless today (mock mode), breaks silently when production API mode is activated.

**`send_notification` returns `success: True` while crashing a background thread on titles >64 chars**

File: `scripts/system_tool.py` line 115.

Plyer raises `ValueError: string too long (1000, maximum length 64)` on a daemon thread. The exception propagates outside the `except Exception` block in `send_notification` because it fires asynchronously. No truncation guard. Caller gets false `{"success": True}` while the notification is silently dropped.

---

### P2 — Hardening for scale

**`parse_po` calls Ollama for zero-byte input — silent empty-POData result**

File: `adapters/po_parser.py` line 293.

Zero bytes passes the 10 MB size guard, decodes to empty string, and proceeds to Ollama. Ollama returns `{}`. `_build_po_data` silently produces a `POData` with all None fields and zero line items — an invalid order stored in the DB. Fix: reject empty content before the size guard.

**`matrix_expander` misidentifies quantity cells as size headers**

File: `adapters/matrix_expander.py`, `_find_header_line()`.

`_SIZE_TOKEN_SET` includes `"0"` through `"20"` and `"28"` through `"44"` (numeric women/jeans sizes). Any row with two cells containing values in those ranges (e.g., a quantity row) triggers the header detector. Observed: matrix with no header row where row `["Red", "5", "10", "15", "20"]` is treated as the size header, producing wrong skus/sizes/quantities for all subsequent rows.

**Orchestrator `get_order()` result used without None check**

File: `manager/orchestrator.py` lines 213–221.

`get_order()` returns `dict | None`. Nine chained `.get()` calls on the result have no None guard. A DB miss (race condition, manual deletion) raises `AttributeError` and crashes the cycle.

---

### P3 — Polish

**28 ruff errors — all auto-fixable**

7x F541 bare f-strings, 17x F401 unused imports across 9 files, 3x F841 dead variables (the HL parent ID vars — symptoms of the P0 bug). Run `ruff check --fix` to clear all.

---

## Flaky / order-dependent tests

None. 5 runs x 173 tests — 100% deterministic pass rate.

---

## Memory / resource leaks

None. SQLite WAL mode handles concurrent async writes cleanly. 50-order + 50-audit concurrent write test: zero errors, zero lost writes. Each `aiosqlite.connect()` opens and closes atomically. No leaked handles or connections observed.

---

## Recommendations

1. **[P0] Fix EDI 856 HL parent IDs** in `adapters/edi_856_asn.py`. Replace the two `hl_counter - 1` calls with `order_hl_id` (for tare) and `tare_hl_id` (for pack). Add a 2-pallet x 2-carton test asserting the exact HL chain.

2. **[P1] Add mock branch to `EmailAgent.connect()`** — skip IMAP when `config.email_backend == "mock"`, inject a synthetic empty inbox. Unblocks CI and dev environments.

3. **[P1] Fix `APIA2000Client` constructor** — either accept `api_url`/`api_key` as init params or remove the kwargs from the orchestrator call. Eliminates the silent misconfiguration on API mode activation.

4. **[P1] Truncate notification title** — add `title = title[:64]` before `notification.notify()` in `send_notification`. Prevents the background-thread crash.

5. **[P2] Reject empty content in `parse_po`** — add `if not content.strip(): raise ValueError("Attachment is empty")` as the first guard.

6. **[P2] Guard `get_order()` result against None** in orchestrator — raise or log-and-skip if row is None.

7. **[P2] Fix `_find_header_line` numeric false positives** — require that a valid header line contains at least one *alphabetic* size token (XS/S/M/L/XL/XXL) alongside numeric ones, or require 3+ distinct tokens. Pure-numeric size tokens are ambiguous with quantity data.

8. **[P3] Run `ruff check --fix`** — clears all 28 auto-fixable errors in under 5 seconds.
