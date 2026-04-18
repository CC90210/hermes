---
tags: [hermes, skill]
---

# SKILL — Invoice Generation and Delivery

> How Hermes retrieves invoices from A2000 and delivers them to customers.

## Flow

```
order status: ENTERED
    ↓
POSAgent.retrieve_invoice(order_id, a2000_client)
    ↓
a2000_client.get_invoice(order_id)   → PDF bytes
    ↓
Save to {LOG_DIR}/invoices/{order_id}.pdf
    ↓
Return Path object
    ↓
EmailAgent.send_invoice(order_id, invoice_path)
    ↓
order status: EMAILED
```

## A2000 Invoice Retrieval

`get_invoice(order_id)` returns raw PDF bytes. The behavior differs by mode:

- **mock:** Returns a stub PDF string (`%PDF-1.4 mock invoice...`). Valid enough
  for pipeline testing, not a real PDF document.
- **api:** Not yet implemented (NotImplementedError). Awaiting GCS API docs.
- **edi:** Not applicable. In EDI mode, the vendor sends an 810 (invoice) document
  back via AS2/VAN. Hermes does not fetch it — it arrives inbound and requires a
  separate 810 handler (Phase 2).
- **playwright:** Not yet implemented.

## Disk Storage

Invoices are written to `{LOG_DIR}/invoices/{order_id}.pdf`. The `LOG_DIR`
defaults to `./logs`. The `invoices/` subdirectory is created automatically
(`mkdir(parents=True, exist_ok=True)`).

Invoice files are:
- Named by internal `order_id` (integer), not PO number — avoids filename collisions
  if the same PO is resubmitted
- Never deleted by Hermes — the client's backup system handles retention
- Not committed to git (`logs/` is in `.gitignore`)

## SMTP Delivery

After the PDF is on disk, `EmailAgent.send_invoice()` sends it:

```python
await email_agent.send_invoice(
    to=customer_email,
    subject="Invoice for PO-XXXX",
    body="...",
    attachment=pdf_bytes,
    filename=f"invoice_{order_id}.pdf",
)
```

The customer email comes from the `customer_email` field on the orders row, which
was extracted from the original PO by the parser.

The audit log entry written by `send_invoice()`:
```json
{"to": "customer@example.com", "subject": "Invoice for ...", "file": "invoice_42.pdf"}
```

## Failure Modes and Retries

**A2000 unreachable at invoice fetch:**
- `get_invoice()` raises an exception
- Orchestrator catches at Step 4, sets order status to FAILED
- On next `handle_failures()`, order is retried (status reset to ENTERED)
- After 3 failures, escalation is sent

**SMTP failure on delivery:**
- `send_invoice()` raises an exception
- Orchestrator catches at Step 5, sets order status to FAILED
- The PDF is already on disk — retrieval does not need to repeat
- The email_queue table is designed for this case (future: auto-retry from queue)

**Invoice already sent (restart scenario):**
- If order status is already EMAILED, `_resume_stalled_orders()` skips it
- The idempotency check is the OrderStatus state machine — EMAILED is terminal

## Obsidian Links
- [[brain/CAPABILITIES]] | [[skills/email-handling/SKILL]] | [[skills/a2000-integration/SKILL]]
