---
tags: [hermes, skill]
---

# SKILL — A2000 Integration

> How Hermes connects to the A2000 POS system. Four modes, one protocol.

## The Four-Mode Ladder

A2000 by GCS Software is an apparel/fashion ERP. Its integration surface depends
entirely on which modules the client has licensed. Hermes works through four modes,
from most to least preferred.

| Mode | Class | When to use | Limitation |
|------|-------|-------------|------------|
| `mock` | `MockA2000Client` | Dev, demo, CI — no live A2000 needed | Returns stub data; no real orders |
| `api` | `APIA2000Client` | If vendor REST API is provisioned | Awaiting GCS credentials (stubs only) |
| `edi` | `EDIA2000Client` | If A2000 instance has EDI module active | Fire-and-forget; no invoice retrieval |
| `playwright` | `PlaywrightA2000Client` | Last resort — screen automation | Brittle; requires selector recording |

Start every deployment on `mock`. Move to `edi` once the client's A2000 EDI module
is confirmed active and tested. Move to `api` if/when GCS provides REST credentials.

## Mode Selection

The mode is resolved at startup from `A2000_MODE` env var. The factory function
`get_a2000_client(mode)` in `adapters/a2000_client.py` handles this:

```python
# .env
A2000_MODE=mock     # or: api | edi | playwright
```

The Orchestrator calls `_build_a2000_client(config.a2000_mode)` once at init and
holds the result. The active client is injected into `POSAgent` per-call —
never hardcoded in the agent.

## The A2000ClientBase Protocol

Every adapter MUST implement all abstract methods on `A2000ClientBase`:

```python
async def create_order(self, po: POData) -> OrderResult
async def get_order(self, order_id: str) -> dict
async def get_invoice(self, order_id: str) -> bytes   # PDF bytes
async def print_order(self, order_id: str) -> bool
async def validate(self) -> None                      # raise on bad connection
async def is_reachable(self) -> bool
```

`OrderResult` fields: `order_id: str`, `success: bool`, `message: str`,
`invoice_number: Optional[str]`.

Breaking the `A2000ClientBase` contract — adding required arguments, changing
return types — is a critical violation. All four adapters plus any future
adapters must be substitutable (Liskov substitution principle).

## EDI Mode Details

`EDIA2000Client` generates X12 850 documents and writes them to `EDI_OUTPUT_DIR`
for AS2 or VAN pickup. The generated file includes:

- Full ISA/GS envelope with configurable sender/receiver IDs
- BEG segment (PO number, order date)
- DTM segment (ship date, if present)
- N1/N3/N4 segments for bill-to and ship-to addresses
- PO1 segments for each line item (qty, unit price, UPC, SKU, description)
- CTT totals + SE/GE/IEA trailer

Required env vars for EDI mode:
```
EDI_OUTPUT_DIR=./storage/edi_out
EDI_SENDER_ID=LOWINGER
EDI_RECEIVER_ID=A2000
```

EDI mode limitations: `get_order()`, `get_invoice()`, `print_order()` all raise
`NotImplementedError`. Invoices in EDI mode arrive as inbound 810 documents via
the VAN — a separate inbound EDI handler is needed for that path (not yet built).

## Fallback Behavior

If the configured mode fails at startup (`validate()` raises), the Orchestrator
logs the error and exits — it does not fall back to mock silently. Silent fallback
to mock in production would cause a dangerous false sense of operation.

If a client deployment needs automatic fallback (e.g. try `api` then `edi`),
that logic belongs in the Orchestrator's `_build_a2000_client`, not in the adapters.

## Adding a New Adapter

1. Create `adapters/a2000_<name>.py`
2. Subclass `A2000ClientBase` and implement all abstract methods
3. Add to `_MODE_MAP` in `adapters/a2000_client.py`
4. Add to `_build_a2000_client()` in `manager/orchestrator.py`
5. Add tests in `tests/adapters/`
6. Update `brain/CAPABILITIES.md` POS Operations table

## Obsidian Links
- [[brain/ARCHITECTURE]] | [[brain/CAPABILITIES]] | [[skills/po-parsing/SKILL]]
