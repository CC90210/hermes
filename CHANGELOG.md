# Changelog

All notable changes to Hermes will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-16

### Added

- Initial scaffold of Agent Operating System
- Email agent (IMAP/SMTP via Outlook 365) — polls inbox for purchase orders,
  filters by subject tokens and attachment filenames, marks processed emails as
  read, and sends invoices back to the originating address
- POS agent with A2000 adapter (4 modes: mock, api, edi, playwright) —
  validates PO data, enters orders into A2000, retrieves invoice PDFs, and
  handles print commands
- LLM-based PO parser using Ollama (qwen2.5:32b) — supports PDF, XLSX/XLS,
  X12 EDI 850, HTML, and plain text; extracts structured `POData` with line
  items via a zero-temperature JSON prompt
- Manager bot orchestrator with health checks — 5-step pipeline
  (email_received → po_parsed → order_entered → invoice_retrieved →
  invoice_emailed), stalled-order recovery, failure escalation via email, and
  SIGINT/SIGTERM clean shutdown
- SQLite local storage with audit logging — WAL mode, foreign keys, `orders`,
  `order_lines`, `audit_log`, and `email_queue` tables; full CRUD helpers and
  `OrderStatus` / `EmailQueueStatus` enums
- Demo mode for end-to-end testing without external dependencies — A2000 mock
  client generates deterministic order IDs and stub invoice PDFs
- Comprehensive test suite (pytest) with async support and fixture samples
  (CSV, plain text PO documents)
- Documentation: build plan, case studies, security model, and trial terms
- `start.bat` Windows launcher and `.env.template` for configuration
