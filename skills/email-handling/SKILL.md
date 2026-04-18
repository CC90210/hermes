---
tags: [hermes, skill]
---

# SKILL — Email Handling

> Email operations playbook. Inbound via IMAP, outbound via SMTP.

## IMAP Poll Strategy

`EmailAgent.poll_inbox()` runs at the start of every cycle. The strategy:

1. Search `UNSEEN` — only emails the IMAP server has not flagged as seen
2. Fetch `ENVELOPE` + `BODY[]` for matched UIDs in a single roundtrip
3. For each message, check subject tokens AND attachment filenames
4. Return only emails that pass at least one PO signal check

**Subject tokens (case-insensitive):** `"po"`, `"purchase order"`, `"order #"`, `"order#"`

**Attachment filename tokens:** `"po"`, `"purchase"`, `"order"`, `"purch"`
with extensions: `.pdf`, `.xlsx`, `.xls`, `.csv`

An email passes if subject OR attachment matches — not both required.

## Idempotency via UID Tracking

IMAP UIDs are stable within a mailbox session. Hermes stores the email UID as
`raw_email_id` on the orders row. This means:

- If Hermes restarts mid-cycle, UNSEEN emails are re-fetched but the existing
  `raw_email_id` prevents a duplicate `create_order` call
- The caller in the Orchestrator should check for existing orders with the same
  `raw_email_id` before calling `parse_and_persist` (this check is currently
  handled at the DB level via the `raw_email_id` column — add a UNIQUE constraint
  on this column if duplicate-safety needs hardening)

## SMTP Send Pattern

Outbound email (invoice delivery and alerts) uses SMTP with STARTTLS:

```
Host: EMAIL_SMTP_HOST (default: smtp.office365.com)
Port: EMAIL_SMTP_PORT (default: 587)
Security: STARTTLS (explicit — not SMTPS)
Auth: LOGIN with EMAIL_USER + EMAIL_PASSWORD
```

Both `send_invoice()` and `send_alert()` use synchronous smtplib wrapped in
`asyncio.get_running_loop().run_in_executor(None, ...)`. This keeps the
async pipeline non-blocking without requiring an async SMTP library.

## Error Handling

**Connection drops:** `IMAPClient` is not automatically reconnected. If `_imap is None`
when `poll_inbox()` is called, a `RuntimeError` is raised. The Orchestrator catches
this at cycle level and logs it — the cycle returns early with 0 results. The
EmailAgent will reconnect on the next `setup()` call (which happens only at Orchestrator
startup). For production resilience, add a reconnect check in `poll_inbox()`.

**Auth failures (IMAP):** `IMAPClient.login()` raises `imapclient.exceptions.LoginError`.
This propagates through `connect()` and causes Orchestrator `setup()` to fail-fast
at startup. Correct credentials must be set before launch.

**Auth failures (SMTP):** `smtplib.SMTPAuthenticationError` propagates from `_sync_send_invoice`.
The Orchestrator catches this in the Step 5 `except` block and sets the order to FAILED.
The email_queue table exists for retry — currently not wired for automatic SMTP retry;
that is a future enhancement.

**Bounces:** Not currently detected. Hermes sends and logs but does not monitor
for bounce/NDR responses. Add bounce detection by polling the inbox for auto-reply
indicators if the client has high bounce rate concerns.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | `outlook.office365.com` | IMAP server |
| `EMAIL_USER` | (required) | Full email address |
| `EMAIL_PASSWORD` | (required) | App password (not account password if MFA is on) |
| `EMAIL_IMAP_PORT` | `993` | IMAP over SSL |
| `EMAIL_SMTP_HOST` | `smtp.office365.com` | SMTP server |
| `EMAIL_SMTP_PORT` | `587` | SMTP with STARTTLS |

For Outlook 365 with MFA, `EMAIL_PASSWORD` must be an app-specific password
generated from the Microsoft account security settings.

## Obsidian Links
- [[brain/CAPABILITIES]] | [[brain/AGENTS]] | [[skills/invoice-generation/SKILL]]
