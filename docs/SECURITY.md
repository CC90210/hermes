# Hermes — Security Architecture
**OASIS AI Solutions | One-Page Security Overview**

---

## The Plain-English Version

> **Hermes is a digital filing cabinet for your business data.**
> The cabinet is locked with military-grade encryption. The cabinet is backed up to a separate, encrypted location every six hours so nothing is ever lost. **You're the only one with the key.** When Hermes needs to think — to read a PO, to draft an email — he asks an AI provider through a legally binding agreement that says: *process this, then forget it. Don't store it. Don't train on it. Don't share it.*

The cloud isn't the risk. **Unaccountable storage is the risk.** We use providers with binding contracts and a financial reason to honor them — leaking your data would expose them to lawsuits in the millions. That's a stronger safety net than most local IT setups.

---

## Security Layers

### 1. Two-Key Encryption on Sensitive Transfers
Sensitive data — credentials, customer records, order details — is protected by a **two-set encryption key system**. Even if a hacker intercepted a transfer, they would see scrambled gibberish. Even if they obtained the encrypted file off your machine, they would still need a second key to decipher it. The realistic paths to break this are exhaustive brute-force attacks (computationally infeasible today) or future quantum computing — and at that point, no hosting model anywhere on Earth is safe.

**What this means:** Hermes meets the security bar that real-world threats actually require. We don't oversell the threat model.

---

### 2. Encrypted Local Vault
All PO data, order history, customer records, and audit logs are stored in a SQLite database with **AES-256 encryption at rest** (via SQLCipher). The database file on disk is unreadable without the encryption key, which is stored separately and never committed to code.

**What this means:** If someone physically accessed your machine and copied the database file, they would have an encrypted blob — not your business data.

---

### 3. Encrypted Backups Every 6 Hours
Automated, encrypted snapshots of your business data are written to a separate provider every six hours. This protects against ransomware, hardware failure, or accidental deletion. Backups are encrypted with the same key system as the live vault — the backup provider sees ciphertext, never plaintext.

**What this means:** A single failure (drive crash, ransomware attack, accidental delete) cannot take you down. You can roll back any change, any day.

---

### 4. Cloud AI Use — Under Legally Binding Agreements
The intelligence layer (parsing POs, drafting emails) uses enterprise AI providers — **Anthropic (Claude) and/or OpenAI (GPT)**. These providers are:

- **SOC 2 Type II certified** — independently audited for security controls.
- **Bound by Data Processing Agreements (DPAs)** — they cannot store your data, train models on it, or share it with third parties.
- **Liable.** If your data leaks because they failed to honor the DPA, they are exposed to legal action with real financial consequences. The contract is the safety net, not just our trust.

**What this means:** Your POs are processed in the cloud, but they vanish from the provider's systems the moment the response is returned. There is no "cloud copy" sitting on a server somewhere.

---

### 5. Optional: Fully Local AI (Air-Gapped)
For clients who want to remove the cloud entirely, the AI itself can run on a dedicated machine in your office with **no outbound internet calls during processing**. This requires a workstation upgrade (~$2,500 one-time) and is **not required** for the trial or for production use. It is offered as an option for the highest-paranoia setups (defense, regulated finance, healthcare).

**What this means:** You can start with the cloud-backed setup today and switch to fully local later — same Hermes, same workflow, same data.

---

### 6. Credential Management
API keys, email credentials, and database passwords are stored in a single encrypted file (`.env.agents`) on your machine. This file is:
- Never committed to any code repository
- Never transmitted anywhere
- Readable only by your Windows account
- Protected by the same two-key encryption system

**What this means:** No secrets are baked into the code. If you rotate a password, you update one file.

---

### 7. Complete Audit Trail
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

### 8. Access Control
The system runs under your Windows user account. It requires no elevated administrator privileges to operate. OASIS AI does not have standing access to your machine — remote support sessions happen only when you initiate them and grant explicit permission for that session.

**What this means:** You are always in control. We can see your screen only when you say so.

---

### 9. Data Retention
Retention policies are configurable. By default:
- Processed PO records: retained 7 years (standard business records requirement)
- Audit logs: retained 2 years
- Raw email content: deleted after successful processing

You can adjust these policies. You own the data, and you control how long it is kept.

---

### 10. Compliance Posture
Hermes is designed for businesses that handle:
- EDI data (ANSI X12 standards compliance)
- Financial records and invoicing
- Personally identifiable information (buyer contacts, account numbers)
- Proprietary pricing and inventory data

The encrypted-vault, audit-logged, DPA-bound architecture meets the spirit of SOC 2 data handling principles. Combined with our cloud providers' own SOC 2 Type II certifications, the end-to-end posture is enterprise-grade without requiring you to build enterprise infrastructure.

---

## Summary

| Security Property | Implementation |
|-------------------|---------------|
| Local data vault | AES-256 (SQLCipher) on your machine |
| Two-key encryption | Two-set key system on sensitive data |
| Backup cadence | Every 6 hours, encrypted, separate provider |
| AI provider posture | SOC 2 Type II + binding DPAs (no storage, no training, no sharing) |
| Credential storage | Encrypted `.env.agents` file, never in code |
| Audit logging | Every action, timestamped |
| Remote access | On-demand, operator-initiated only |
| Optional offline mode | Available — workstation upgrade required |

---

## The One-Sentence Pitch (for Emmanuel)

> Your data lives in an encrypted vault on your computer, the AI that helps process it is bound by a contract that says "no copies allowed," and everything is backed up every six hours so nothing is ever lost — and if you want to take the cloud out of the equation entirely, that's a switch we can flip later.

---

*Questions about security architecture? Contact Conaugh McKenna at conaugh@oasisai.work*
