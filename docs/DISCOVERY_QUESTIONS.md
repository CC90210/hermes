# Hermes — Discovery Questions
**OASIS AI Solutions | Pre-Deployment Discovery Session**
**Client: Emmanuel Lowinger | Prepared by Conaugh McKenna**

---

> These questions are for the 30-minute setup call. They determine the fastest and most reliable integration path into A2000 and Outlook. The more context we have before we start, the faster the build.

---

## Section 1: A2000 POS System

These questions determine which integration tier we use — API, EDI, or screen automation.

1. Which version of A2000 are you running? (Check under Help > About in the application)
2. Is your A2000 provided by GCS Software? (We want to confirm we are looking at the right vendor documentation)
3. Do you currently have API access enabled on your A2000 licence, or do you have access to an A2000 administrator account?
4. Is EDI currently set up in A2000? Do you receive any orders via EDI today, or has EDI ever been configured?
5. What database is A2000 running on — Oracle or SQL Server? (This is usually visible in your IT documentation or A2000 system settings)
6. How many users log into A2000 daily? Is it just you, or do you have staff entering orders?
7. When you enter an order manually today, approximately how many fields do you fill in before the order is saved? (Helps us scope the automation map)
8. Are there any custom fields or modules in your A2000 setup that are specific to your business (e.g., a custom field for Walgreens account codes)?

---

## Section 2: Email Environment

These questions determine how we connect to your inbox securely and reliably.

1. Are you using Microsoft 365 (cloud-based Outlook) or an on-premises Exchange server?
2. Approximately how many PO emails do you receive per day? Per week? (We want to understand the volume the agent will process)
3. What formats do your POs arrive in? (Select all that apply)
   - PDF attachment
   - Excel/CSV attachment
   - EDI file attachment
   - Order details written in the email body
   - A combination — depends on the buyer
4. Do Walgreens and your other major buyers always send from the same email domain, or do their sending addresses vary?
5. Do you have any email rules or folders set up in Outlook today to sort incoming POs? (If so, we can integrate with those rather than replacing them)
6. Is there a shared inbox or distribution list that receives POs, or do they all arrive at your personal address?
7. Are there any emails in your inbox right now that are NOT POs but look similar (e.g., order updates, shipping confirmations, cancellations)? These help us train the classifier.

---

## Section 3: Current Workflow

Walking through one real order end-to-end is the most valuable 10 minutes of the setup call.

1. Can you walk us through one PO from the moment it arrives in your inbox to the moment the invoice is sent? We want to see every click and every system you touch.
2. How long does it typically take to process one order manually — from opening the email to confirming the order in A2000?
3. What are the most common errors or pain points in the current process? (Misread quantities? Wrong SKU? Pricing mismatches?)
4. When you cannot process orders (vacation, trade show, weekend), what happens? Do orders queue up? Does someone else cover? Are buyers notified?
5. Are there order types that are more complex and might need manual review — high-value orders, special pricing, rush orders, backordered items?
6. Do you experience seasonal spikes in order volume? Which months are heaviest?
7. How do you currently handle a PO where a line item is out of stock or cannot be fulfilled at the requested quantity?

---

## Section 4: Integration Preferences and Environment

These questions determine the deployment environment and notification preferences.

1. Is there a dedicated computer that runs A2000 continuously during business hours? Or is A2000 installed on your personal workstation?
2. Would you prefer the agent to run on the same machine as A2000, or on a separate computer? (Both work — separate is slightly cleaner)
3. What is your preferred notification method when the agent needs your attention?
   - Email to your inbox
   - SMS text message
   - WhatsApp message
   - A daily digest email rather than real-time alerts
4. Do you have an IT person or managed IT provider, or do you handle the technical side yourself?
5. Is your A2000 instance on a local server (your office network only) or accessible remotely via VPN?
6. Are there any other software systems we should be aware of — a separate CRM, an inventory management tool, a shipping platform?

---

## Section 5: Success Definition

The most important section. We build toward your definition of success, not ours.

1. What does "this is working" look like to you? Describe your ideal outcome in plain language after the system has been running for a month.
2. How many orders per day would make this system obviously worth it? What is the volume at which the time savings become undeniable?
3. What is the single most frustrating part of the current PO process that you most want eliminated?
4. Is there anything about the automation that would make you uncomfortable — for example, would you want to review every order before it is confirmed in A2000, or are you comfortable with straight-through processing for routine orders?
5. What would genuinely blow your mind — a capability or outcome that would make you talk about this system to other business owners?
6. Are there other people in your business (staff, accountant, operations manager) who would interact with or need to trust this system? If so, what would they need to see to be comfortable with it?

---

## Pre-Call Prep Request

Before our 30-minute setup call, please have the following ready if possible:

- [ ] A2000 open on screen (so we can see the order entry screens together)
- [ ] 3–5 sample PO emails in your inbox (we may ask you to forward these to conaugh@oasisai.work)
- [ ] Your A2000 version number (Help > About)
- [ ] 10 minutes of uninterrupted time to walk through one real order manually

This call is the foundation of everything we build. The more honest and detailed your answers, the faster we deliver a system that actually fits how your business works.

---

*Conaugh McKenna — Founder, OASIS AI Solutions*
*conaugh@oasisai.work | oasisai.work*
