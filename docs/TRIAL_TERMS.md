# Hermes — 14-Day Free Trial Terms
**OASIS AI Solutions | Prepared for Emmanuel Lowinger**

---

## The Offer

OASIS AI Solutions will deploy a fully functional version of Hermes — including the Email Agent, A2000 integration, Invoice Loop, and Manager Bot — at no cost for a 14-day trial period. You get the complete system. If it processes your orders reliably and saves you meaningful time, we move to a maintenance retainer. If it does not meet the success criteria below, we remove everything cleanly and you owe nothing.

No contracts. No lock-in. No risk.

---

## What Is Included in the Trial

| Component | Included |
|-----------|---------|
| Full system deployment on your hardware | Yes |
| Email Agent (Outlook inbox monitoring and PO classification) | Yes |
| POS Integration (A2000 order entry — real or mock depending on API access) | Yes |
| Invoice retrieval and outbound email | Yes |
| Manager Bot (orchestration, health checks, failure alerts) | Yes |
| Setup call and configuration walkthrough | Yes |
| 14 days of monitoring and support from OASIS AI | Yes |
| Documentation and setup guide | Yes |

---

## What We Need From You

To deploy the system and run a meaningful trial, we need the following from you before the setup call:

**Access**
- A2000 API credentials (preferred) or A2000 admin login for screen automation fallback
- Outlook email credentials or Microsoft 365 OAuth consent (we walk you through this — takes 5 minutes)

**Sample Data**
- 3–5 representative PO emails with attachments (from Walgreens or other regular buyers)
- These can be real historical POs — we use them to configure the parser before going live

**Your Time**
- 30-minute setup call to walk through one order manually and confirm the integration approach
- Availability to review the first 5 live orders so we can confirm accuracy together

**Hardware**
- A Windows computer with 16GB+ RAM that can run during business hours (the computer running A2000 works fine)

---

## Trial Success Criteria

At the end of 14 days, we evaluate the trial against these benchmarks:

| Criteria | Target |
|----------|--------|
| PO processing accuracy | End-to-end, correct order entry with no manual correction needed |
| Error rate | Less than 5% of orders require manual intervention |
| Invoice turnaround | Invoice emailed to buyer within 15 minutes of PO receipt |
| System uptime | Agent running reliably without daily restarts |
| Operator intervention | You should receive fewer than 3 escalation alerts per week for routine orders |

If we hit these benchmarks, the system is working. If we fall short in any area, we diagnose and fix before asking you to consider a retainer.

---

## After the Trial

If the trial succeeds, we move to a monthly maintenance retainer. The retainer covers:

- System monitoring and uptime assurance
- Error triage and resolution (within 24 hours for critical issues, 72 hours for non-critical)
- Prompt and parser tuning as your PO formats evolve
- A2000 compatibility updates when you upgrade versions
- Quarterly review call: throughput trends, improvement recommendations
- New buyer onboarding (adding a new customer's PO format to the parser)

**Retainer pricing** is based on your order volume and the number of active integrations. We scope this after the trial so the price reflects your actual usage — not a worst-case estimate. Typical range for a business at your scale: **$300–600/month.**

There is no development cost charged for Phase 0–4 work completed during the trial. You pay only the ongoing retainer for the system that is running on your machine.

---

## Data Handling During the Trial

- All data processed during the trial stays on your machine
- OASIS AI may access your system remotely for setup and troubleshooting — only with your explicit permission per session
- We do not retain copies of your POs, order data, or customer information
- At trial end (pass or fail), no data is transferred out — it remains in your encrypted local database

---

## Exit Clause

If you decide the system is not right for your business at any point during or after the trial:

1. We provide a clean removal script that uninstalls all components
2. Your SQLite database (your order history and audit logs) remains on your machine — it is your data
3. Your A2000 data is untouched — the agent never modifies historical records, only creates new orders
4. No cancellation fees. No notice period required.

You will not be left with orphaned software, hidden files, or ongoing costs.

---

## Next Steps

To start the trial, we need:

1. **Confirmation from you:** Reply or call to confirm you want to proceed
2. **Setup call booked:** 30 minutes — we will send a calendar link
3. **Sample POs:** Email 3–5 historical PO files to conaugh@oasisai.work before the call
4. **Access prep:** We will walk you through the A2000 and Outlook credential steps on the call

**Target go-live:** Within 48 hours of the setup call.

---

*Conaugh McKenna — Founder, OASIS AI Solutions*
*conaugh@oasisai.work | oasisai.work*
