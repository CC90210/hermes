# Security Policy — Hermes (Commerce Agent)

Hermes is the commerce agent of the OASIS AI family — deployed **on the
client's own machine**, not on OASIS AI infrastructure. It reads purchase
orders, enters them into the client's ERP (A2000, Shopify, Square,
WooCommerce, custom), generates ASNs and GS1-128 carton labels, and
catches chargeback-risk mismatches before they cost money. Client
commerce data stays on the client's machine.

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Please email **security@oasisai.work** (preferred) or
**conaugh@oasisai.work** (fallback) with:

- A description of the issue
- Steps to reproduce (or a proof-of-concept)
- The affected version or commit SHA
- Your assessment of impact — especially anything that could affect
  customer order integrity, chargebacks, or financial reconciliation

**Response SLA**

| Stage | Target |
|-------|--------|
| Initial acknowledgement | within 48 hours |
| Severity triage | within 5 business days |
| Fix in `main` for critical/high | within 14 days |
| Order-integrity or chargeback-risk bugs | accelerated — usually 72 hours |
| Coordinated public disclosure | 90 days from report, or sooner if a fix ships |

We will credit you in the fix commit and changelog unless you ask to stay
anonymous.

## Supported Versions

Only the latest commit on `main` is actively maintained. Forks and older
tags are not patched. If you are running a pinned commit older than 30
days, pull `main` before reporting — the issue may already be fixed.

## Security Posture

Hermes is installed via `install.ps1` at the repo root (Windows) or
equivalent shell on macOS/Linux. The shared OASIS AI credential posture
applies:

### Credential handling

- All secrets live in a single `.env.agents` file per install — never
  in source, never in git history, never in CI logs.
- `.env.agents` is in `.gitignore` and `.git/info/exclude`.
- On POSIX the file is `chmod 0600` (owner read/write only). On Windows,
  NTFS ACLs inherit from the user home directory; Hermes is installed
  to run under a dedicated service account where the client has
  administered access control.
- ERP credentials (A2000 login, Shopify private-app tokens, Stripe
  secret keys, Square access tokens) are loaded from `.env.agents`
  at runtime. They are never echoed to stdout, never logged, and never
  written to the session log.

### Secret scanning

- `scan_secrets.py` (via the OASIS AI setup wizard) runs over the
  working tree + git history. Detects 18+ credential shapes including
  Stripe `sk_live_`, Shopify admin-API tokens, JWT, and suspicious
  filenames (`*.pfx`, `credentials.json`, etc.).
- A hardened `.gitignore` blocks `*.env*`, `*_token.txt`,
  `credentials.json`, `service_account.json`, `*.pem`, `*.key`, SSH
  keys, and ERP-configuration files that contain credentials.

### Customer-data locality

This is Hermes's most important commitment:

- **Customer commerce data never leaves the client's machine.** POs,
  invoices, ASNs, carton manifests, and inventory records stay in the
  local SQLite database and the client's own ERP.
- **No telemetry to OASIS AI.** Hermes does not phone home. Error
  diagnostics are written to a local log file; no stack traces, no
  performance metrics, no usage counts are transmitted to OASIS AI.
- **LLM inference only under the customer's API key.** Claude / GPT
  calls use the `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` the customer
  installed. OASIS AI cannot read the traffic.

### Idempotency and order integrity

- Every PO ingestion generates a canonical PO hash. If the same PO is
  reprocessed (retry, duplicate inbox event), the second write is a
  no-op.
- Every ASN dispatch is logged with a monotonic sequence number; a
  missing gap triggers an operator alert before the next ASN ships.
- The chargeback-risk detector runs on every PO and every ASN; flagged
  mismatches pause the automated flow until a human clears them.

### Safety hooks

- `.claude/settings.local.json` registers hooks that block destructive
  shell commands and block any edit that would touch a `.env*` file.
- Every ERP write is append-only to a local audit log.

## Scope for this Agent (Hermes / Commerce)

Hermes is the **commerce back-office** agent, deployed per-client. By
design it can:

- Read inbound purchase orders (email, EDI, API) and enter them into
  the client's configured commerce platform
- Generate ASN (Advance Ship Notice) payloads in the format the
  customer's retail buyer requires
- Generate GS1-128 carton labels and pallet manifests
- Run the chargeback-risk detector over every PO + ASN pairing
- Send weekly summaries to the client's operations lead via their
  chosen support channel (`email`, `chat`, `sms`)
- Maintain a local inventory-position snapshot for clients who enable
  inventory tracking

Hermes **cannot**, by policy:

- Connect to any OASIS AI internal system. It runs isolated on the
  client's machine.
- Share client commerce data with sibling OASIS AI agents (Bravo,
  Atlas, Maven, Aura). The cross-agent inbox is not wired into
  Hermes by default.
- Authorize new payment methods or raise credit limits. Its commerce
  platform permissions are read/write for orders only — not for
  financial instruments.
- Modify the client's retail-buyer contracts or pricing tables without
  explicit operator approval recorded in the audit log.

## Out of Scope

This policy covers Hermes's own code and install path. It does **not**
cover:

- The client's ERP configuration or access controls
- The client's email server or EDI integration setup
- Misuse of an ERP credential the client has granted to a third party
- The client's physical shipping and warehousing operations
- Vulnerabilities in upstream dependencies — tracked via GitHub
  Dependabot and patched in regular releases

## Coordinated Disclosure

Please give us a reasonable window to fix before public disclosure.
90 days is the default; we will ship a fix faster if we can and will
request an extension only for genuinely complex issues with clear
communication.

**For order-integrity or chargeback-risk bugs — anything where a
software flaw could cause money to move incorrectly or a retail
chargeback to slip through — please mark the subject line
`[HERMES-COMMERCE]` and we will accelerate the fix.**

Thank you for helping keep our agents safe for the businesses that
depend on them.
