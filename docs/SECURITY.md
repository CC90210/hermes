# Hermes — Security Architecture
**OASIS AI Solutions | One-Page Security Overview**

---

## The Core Principle: Your Data Never Leaves Your Network

Every design decision in Hermes starts with one constraint — **no sensitive business data is transmitted to third-party services for processing.** Your purchase orders, customer information, pricing, and financials are yours. They stay on your hardware, under your control.

---

## Security Layers

### 1. Local-First AI Processing
The intelligence layer (Ollama) runs entirely on your machine. When the system reads a PO and extracts line items, that work happens locally — not in OpenAI's data centers, not in any cloud. There is no API call to an external AI service. No vendor sees your Walgreens purchase orders.

**What this means:** Even if a third-party AI vendor were breached tomorrow, your data would not be in their system because it was never sent there.

---

### 2. Encrypted Storage
All PO data, order history, customer records, and audit logs are stored in SQLite with SQLCipher encryption at rest. The database file on disk is unreadable without the encryption key, which is stored separately and never committed to code.

**What this means:** If someone physically accessed your machine and copied the database file, they would have an encrypted blob — not your business data.

---

### 3. No Cloud Data Egress
The only external network calls this system makes are to services you already own and operate:
- Your Outlook account (reading your own inbox, sending from your own address)
- Your A2000 instance (on your local network or VPN)

There are no calls to cloud databases, analytics platforms, logging services, or AI APIs with your data.

**What this means:** Your firewall sees nothing unusual. Your IT posture does not change.

---

### 4. Credential Management
API keys, email credentials, and database passwords are stored in a `.env` file on your machine. This file is:
- Never committed to any code repository
- Never transmitted anywhere
- Readable only by the user account running the system
- Documented — you know exactly what credentials the system holds

**What this means:** No secrets are baked into the code. If you rotate a password, you update one file.

---

### 5. Complete Audit Trail
Every action the system takes is logged with full context:

```
2026-04-16 09:14:22 | email_agent    | PO #WG-88291 received from buyer@walgreens.com
2026-04-16 09:14:31 | parser         | Extracted 12 line items — confidence 98%
2026-04-16 09:15:04 | a2000_adapter  | Order entered — A2000 ID #44821
2026-04-16 09:17:12 | invoice_agent  | Invoice #INV-44821 retrieved and emailed to buyer
```

Every log entry includes timestamp, agent name, action, and result. Nothing happens silently.

**What this means:** Full accountability. If a question ever arises about an order, you have a complete, timestamped record of every step.

---

### 6. Access Control
The system runs under your Windows user account. It requires no elevated administrator privileges to operate. OASIS AI does not have standing access to your machine — remote support sessions happen only when you initiate them and grant explicit permission for that session.

**What this means:** You are always in control. We can see your screen only when you say so.

---

### 7. Data Retention
Retention policies are configurable. By default:
- Processed PO records: retained 7 years (standard business records requirement)
- Audit logs: retained 2 years
- Raw email content: deleted after successful processing

You can adjust these policies. You own the data, and you control how long it is kept.

---

### 8. Compliance Posture
Hermes is designed for businesses that handle:
- EDI data (ANSI X12 standards compliance)
- Financial records and invoicing
- Personally identifiable information (buyer contacts, account numbers)
- Proprietary pricing and inventory data

The local-first, encrypted, audit-logged architecture meets the spirit of SOC 2 data handling principles without requiring a cloud environment to achieve it.

---

## Summary

| Security Property | Implementation |
|-------------------|---------------|
| Data processing location | Your machine only |
| AI vendor access to your data | None (Ollama is local) |
| Storage encryption | SQLCipher (AES-256) |
| Credential storage | Local `.env` file, never in code |
| Audit logging | Every action, timestamped |
| Remote access | On-demand, operator-initiated only |
| Cloud dependencies | None for data processing |

---

*Questions about security architecture? Contact Conaugh McKenna at conaugh@oasisai.work*
