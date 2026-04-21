# Discovery Questions for Emmanuel

> The answers to these determine which phases of Hermes we turn on for you, in what order, and how fast we can go live.
> **Priority**: answer sections 1-3 first. Sections 4-7 can come within 2 weeks of kickoff.

## Section 1: Compliance Reality (CRITICAL — answer first)

The biggest value Hermes provides is keeping you compliant with Walgreens (and similar retailers) so their automated chargeback system doesn't take weekly bites out of your margin. Industry data: small wholesalers without proper EDI compliance lose $50K-$150K/year to chargebacks. Your answers here determine whether Hermes is a "nice to have" or a "save six figures in year one" tool.

1. **Annual chargeback exposure**: roughly how much do Walgreens (and other retailers) deduct from your payments per year? Ballpark is fine.
2. **Current ASN process**: are you sending Advance Ship Notices (EDI 856) for Walgreens shipments today? If yes, how — manual through the Walgreens portal, an EDI broker, or in-house?
3. **Carton labels**: do you generate GS1-128 (SSCC-18) carton labels today? If yes, on what printer + software? If no, how are you labeling cartons?
4. **Cost Recovery Program**: have you been hit by Walgreens' Cost Recovery Program fines? How often, and roughly how much per quarter?
5. **DSD vs DC**: what % of your Walgreens shipments are Direct Store Delivery (DSD) vs. Distribution Center (DC)?
6. **EDI broker / VAN**: do you currently use an EDI broker (SPS Commerce, TrueCommerce, CrossBridge, Sterling, etc.)? What's the monthly cost?

## Section 2: Your POS System (A2000)

7. **A2000 variant**: is it GCS Software's A2000 (apparel/fashion ERP, US-based) or the Singapore A2000 Solutions ERP? Or a different product we haven't heard of?
8. **EDI module**: is the A2000 EDI module currently licensed and active on your instance? Which transaction sets are configured (850, 855, 856, 810, 820, 832, 852, 997)?
9. **API access**: does GCS Software provide API access to your A2000? Do you have admin-level credentials or an integration partner (Sunrise Integration, Hara Partners, etc.)?
10. **Database**: A2000 runs on Oracle. Do you have direct DB read access (risky — last-resort), or API/EDI only?
11. **Contract pricing**: does A2000 hold customer-specific contract prices? Where (table name if known)?
12. **Credit holds**: does A2000 have a credit-hold flag per customer? How is it set/cleared?
13. **820 reconciliation**: how do you currently match incoming 820 remittances to open invoices? Manual reconciliation?

## Section 3: Email Environment

14. **Outlook stack**: Office 365 (online) or on-premises Exchange?
15. **Email address for POs**: does a dedicated address receive POs (orders@yourdomain.com) or does it come into your personal inbox mixed with everything else?
16. **IMAP access**: does your IT allow IMAP/SMTP connections on port 993/587? If not, what email protocol (Exchange Web Services, Graph API)?
17. **Current PO handling**: walk us through what happens when a PO email arrives today. Who opens it? What tools are used?

## Section 4: Volume and Workflow

18. **PO volume**: average POs per day? Peak week/month?
19. **Average PO size**: line items per PO? Dollar value per PO?
20. **PO format**: are POs arriving as PDF attachments? Excel? EDI X12 (raw)? In the body of the email? A mix?
21. **Customer mix**: top 5 customers by volume? Top 3 retail chains?
22. **Apparel or non-apparel**: are your products apparel/fashion SKUs (with size-color matrix) or flat SKUs (like a unique code per product)?
23. **Matrix POs**: if apparel — do Walgreens POs arrive as a size-color grid, or pre-expanded line items?
24. **Item cross-reference**: do you maintain a buyer-item-code ↔ your-vendor-SKU crosswalk? In Excel? In A2000?

## Section 5: Operations

25. **Notifications**: when Hermes needs you (edge case, failed order, chargeback deadline), should we reach you via email, WhatsApp, SMS, or Slack?
26. **Autonomy level**: for routine clean POs, full autonomous processing (Hermes handles end-to-end, reports summary) — correct? Or does every PO need your eyes first during trial?
27. **Approval workflows**: are there order types that always need human approval (big dollar, new customer, credit-hold customer)?
28. **Return / RGA workflow**: how are returns handled today?
29. **Warehouse integration**: does your warehouse use WMS? Pick tickets print to a specific printer?

## Section 6: Phone Automation (Phase 2, lower priority)

30. **Walgreens store calls**: for the 300-1000 Walgreens store calls you mentioned — what's the actual goal (manager contact, order follow-up, something else)?
31. **Call frequency**: daily, weekly, seasonally?
32. **IVR patterns**: is the Walgreens store IVR structure fairly consistent, or does it vary a lot by store?
33. **Call recording**: any legal/compliance concerns we need to handle (Florida is a two-party-consent state)?

## Section 7: Deployment and Infrastructure

34. **Hermes host machine**: dedicated machine for Hermes (recommended), or same machine as A2000? Spec (RAM, OS)?
35. **Network**: on a LAN with A2000? Any firewalls between Hermes and A2000/email?
36. **Access during trial**: can we remote-access (AnyDesk / TeamViewer / Tailscale) for setup and troubleshooting, or is air-gapped required?
37. **Who owns cloud costs**: the interactive Hermes IDE uses Claude API (~$30-100/mo at moderate use). OK with us billing through, or would you prefer direct to Anthropic?
38. **Technical comfort**: is this you running Hermes day-to-day, or will someone on your team be the operator? What's their technical level?

## Delivery method

Answer inline here, in a follow-up email, or on a voice call — whatever works for you. The 6 questions in Section 1 are the highest priority; everything else we can iterate through.
