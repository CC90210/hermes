# Wholesale Distribution -- Deep Market Research
**Prepared for Hermes scope expansion | OASIS AI Solutions | April 2026**

---

## 1. Real Wholesale Distribution Order Lifecycle

The current Hermes model treats the order lifecycle as a 3-step sequence: PO in, A2000 entry, invoice out. Real wholesale order-to-cash has 16 distinct checkpoints, many generating their own EDI traffic and compliance obligations.

### Full Lifecycle Map

| Stage | What Happens | Automated at Small Wholesaler? | EDI Transaction |
|---|---|---|---|
| 1. PO Receipt and Triage | Inbound from buyer via EDI, PDF, Excel, or customer portal (Walgreens uses SupplierNet) | Partially -- EDI auto-ingests; PDF/Excel still manual at most small shops | EDI 850 |
| 2. Functional Acknowledgment | File-level receipt confirmation sent within minutes of PO receipt | Usually automated by VAN or EDI middleware | EDI 997 |
| 3. PO Acknowledgment | Vendor confirms receipt AND processing -- can accept, reject, or accept with changes. Must be sent within 24-48 hours | Manual at small wholesalers; automated at mid-size | EDI 855 |
| 4. Pricing Validation | Check PO prices match contract, volume tier, or promo pricing. Mismatch triggers 855 change or manual buyer call | Manual -- human cross-references A2000 price file | Internal |
| 5. Credit Check | Does buyer have open credit? Is new PO within limit? Is any balance overdue? | Manual at small shops; automated in mature ERP | Internal |
| 6. Credit Hold and Release | If credit fails, order queues for AR review; released when payment received or limit raised | Manual -- AR manager makes the call | Internal |
| 7. Inventory Check and Allocation | Are ordered SKUs in stock? If partial, ship available or hold for complete fulfillment? Customer priority rules apply | Manual at small wholesalers | EDI 846 (optional) |
| 8. PO Entry into POS/ERP | Order officially created in A2000 -- generates internal order number | Hermes automates this | Internal |
| 9. Pick Ticket and Wave Planning | Warehouse receives pick list; orders batched into waves by carrier/ship date/zone | Manual at small/medium; WMS-driven at large | Internal |
| 10. Warehouse Fulfillment | Picker pulls, packs, confirms quantities. Weight and carton count captured | Manual -- human labor | Internal |
| 11. ASN Generation and Transmission | CRITICAL: Advance Ship Notice sent BEFORE truck leaves dock. Must include SSCC-18 per carton. Walgreens DC: 4 hours before. Store: 1 hour before | Often manual -- this is where most chargebacks originate | EDI 856 |
| 12. Carrier Label and BOL | GS1-128 label printed per carton (SSCC-18 encoded), BOL generated for carrier handoff | Partially automated if WMS present; manual at small shops | Internal |
| 13. Invoice Generation | Issued after ship confirmation; must match PO exactly (three-way match: PO + receipt + invoice) | A2000 generates invoice -- Hermes retrieves and sends | EDI 810 |
| 14. Functional Ack on Invoice | Buyer confirms invoice file received | Automated by buyer EDI system | EDI 997 |
| 15. Payment Remittance | Buyer sends payment detail -- which invoices paid, any deductions taken | Manual reconciliation at small shops | EDI 820 |
| 16. Deduction Resolution | Buyer deducts chargebacks from remittance. Vendor must dispute within 4 weeks or loses the money | Almost entirely manual | Internal |

**Sources:**
- [Cleo -- EDI Order to Cash Overview](https://www.cleo.com/blog/Order-to-Cash-process)
- [Tirnav -- EDI 850, 855, 856, 810 Guide](https://tirnav.com/blog/retail-edi-850-855-856-810-guide)
- [SPS Commerce -- EDI 855 PO Acknowledgment](https://www.spscommerce.com/edi-document/edi-855-purchase-order-acknowledgment/)
- [Commport -- EDI 850 and 855 Explained](https://www.commport.com/edi-purchase-order-and-purchase-order-acknowledgement/)
- [OrderSync -- EDI for Wholesale Distribution](https://ordersync.io/edi-for/wholesale-distribution)

### Automation Reality at Small-to-Mid Wholesaler

At a company of Emmanuel's size:
- **Automated:** EDI 997 functional acks (VAN handles it), invoice generation inside A2000
- **Semi-automated:** EDI 850 ingestion if VAN is configured; carrier label printing if integrated with shipping software
- **Manual:** EDI 855 acknowledgment, pricing validation, credit check, inventory allocation decisions, ASN generation, BOL creation, deduction dispute

Hermes Phase 1-4 automates Stages 1, 8, and 13. Stages 2-7 and 11-12 are untouched and represent the real compliance and chargeback liability surface.

---

## 2. Walgreens Vendor Compliance -- What It Actually Takes

Walgreens launched a formal Cost Recovery Program in 2018 that automatically fines vendors weekly for non-compliance. It runs on their SAP system via SPS Commerce -- not discretionary, not manually administered.

### Vendor Portal

- **SupplierNet** -- primary vendor portal. Contains policies, routing guides, OTFR performance metrics, dispute forms, and the VAIS system for chargebacks.
- URL: [suppliernet.walgreens.com](https://suppliernet.walgreens.com/)
- DSD vendors use a separate SPS Commerce web portal, not SupplierNet directly.
- New vendor discovery: [SupplierOne](https://walgreens.supplierone.co/)

### Mandatory EDI Transaction Sets (ANSI X12, Version 5010)

| Set | Description | Direction | Mandatory? |
|---|---|---|---|
| 850 | Purchase Order | Walgreens to Vendor | Yes -- how POs arrive |
| 855 | PO Acknowledgment | Vendor to Walgreens | Yes -- must respond within 24-48 hrs |
| 856 | Advance Ship Notice (ASN) | Vendor to Walgreens | Yes -- most critical compliance point |
| 810 | Invoice | Vendor to Walgreens | Yes |
| 820 | Payment Remittance | Walgreens to Vendor | Yes -- how deductions are communicated |
| 997 | Functional Acknowledgment | Both directions | Yes -- auto-generated |
| 832 | Price/Sales Catalog | Vendor to Walgreens | Situation-dependent |
| 852 | Product Activity Data | Walgreens to Vendor | For replenishment programs |

Connection method: AS2 preferred, VAN or FTP legacy. Drop-ship routes through Rithum (formerly CommerceHub). Marketplace through LogicBroker.

**Source:** [CrossBridge -- Walgreens EDI Integration Guide](https://crossbridge.rs/blog/walgreens-edi-integration-guide), [TrueCommerce -- Compliant EDI for Walgreens](https://www.truecommerce.com/trading-partner/walgreens/)

### ASN Timing Windows -- The Most Violated Rule

| Fulfillment Type | ASN Must Arrive Before Truck By |
|---|---|
| DC (Distribution Center) | 4 hours |
| Direct Store Delivery (DSD) | 1 hour |

Missing these windows is the single largest chargeback source. Walgreens receiving systems use ASN data to pre-stage dock workers. A late or missing ASN triggers a fine even when the shipment arrives on time.

### Chargeback Formula (Cost Recovery Program, launched 2018)



- Walgreens targets >=95% on-time fill rate; anything below triggers the formula
- 4-week dispute window from notification email
- Dispute submission: SupplierNet > Forms > Vendor Dispute Form
- Dispute email: SupplyChain.Compliance@Walgreens.com
- Valid dispute grounds: Walgreens DC pushed appointment past WSTA (Will Ship to Date), or Walgreens provided insufficient lead time
- Dispute statuses tracked: OPEN, UNDER DISPUTE, CLOSED, REVERSED

**Source:** [SPS Commerce -- Disputing Walgreens Compliance Fines](https://www.spscommerce.com/community/articles/disputing-compliance-fines-at-walgreens), [SupplierWiki -- How to Dispute Deductions](https://supplierwiki.supplypike.com/articles/how-to-dispute-deductions-at-walgreens)

### GS1-128 / UCC-128 Carton Label Requirements

- Format: 4" x 6" thermal, GS1-128 barcode symbology, Code 128
- Each carton gets a unique SSCC-18 (Serial Shipping Container Code): 18 digits, Application Identifier (00)
- Structure: extension digit + GS1 Company Prefix + serial reference + check digit (Modulo 10)
- Required data fields: SSCC-18 with AI (00), PO Number with AI (400), ship-to DC with AI (410), vendor number, carton count
- Minimum print resolution: 203 DPI; 300 DPI recommended; barcode height >= 1 inch; 0.25" quiet zones
- The ASN file and the physical carton label must contain identical SSCC data -- mismatch = automatic chargeback
- Walgreens-specific label template: [Orderful -- Walgreens UCC-128 Support](https://docs.orderful.com/changelog/walgreens-ucc-128-label-support)

**Source:** [JASCI Cloud -- Retail Compliance Labels Guide](https://www.jascicloud.com/blog/retail-compliance-labels-guide), [GS1 US -- SSCC](https://www.gs1us.org/upcs-barcodes-prefixes/serialized-shipping-container-codes), [SPS Commerce -- UCC-128](https://www.spscommerce.com/edi-document/ucc-128-label/)

### DSD vs. DC -- Two Different Operational Programs

| Factor | DSD (Direct Store Delivery) | DC (Distribution Center) |
|---|---|---|
| Delivery destination | Individual Walgreens store | Central Walgreens DC |
| ASN window | 1 hour before arrival | 4 hours before arrival |
| Invoicing | Per-store, complex reconciliation | Centralized |
| Onboarding | SPS Commerce DSD portal | SupplierNet + standard EDI |
| Vendor shelf responsibility | Vendor may be expected to stock shelves | DC handles internal movement |

DSD is significantly harder at small scale: per-store invoicing means dozens of separate invoices per delivery run, and reconciliation against the 820 is a manual nightmare without dedicated tooling.

### Common Chargeback Categories (Ranked by Frequency at Small Vendors)

1. Late or missing ASN -- arrives after the truck or not at all
2. ASN/label data mismatch -- SSCC on carton does not match SSCC in ASN file
3. Short ship or over ship -- quantity in ASN does not match physical receipt
4. Late delivery -- shipment arrives outside the agreed routing window
5. Wrong carrier -- vendor ignores routing guide and chooses own carrier
6. Invoice discrepancy -- invoice price or quantity does not match PO
7. Wrong label format -- not GS1-128, wrong dimensions, or low-quality print
8. Missing PO number -- BOL or label does not include the PO reference

**Source:** [Legacy SCS -- 7 Common Chargeback Mistakes](https://legacyscs.com/common-retail-chargebacks-mistakes-explained/), [Productiv -- Chargeback Prevention](https://getproductiv.com/retail-chargeback-compliance)

---

## 3. A2000 (GCS Software) -- Deep Integration Reality

### Database

A2000 runs on **Oracle**. Confirmed across multiple independent review sources. Not SQL Server. This matters because Hermes Tier 3 (direct DB write) requires Oracle SQL, Oracle JDBC drivers, and navigating Oracle strict transaction semantics. GCS support contract almost certainly voids on unsanctioned direct DB writes.

**Source:** [SoftwareConnect -- A2000 Technical Review](https://softwareconnect.com/apparel-erp/gcs-computers-a2000/), [Top10ERP -- A2000 Profile](https://www.top10erp.org/products/a2000-erp)

### API Reality

- A2000 markets a REST API, Open API, and Open ODBC on their website
- Pre-built connectors cover: Shopify, WooCommerce, Amazon, Joor, NuOrder, UPS, FedEx, DHL, ChannelAdvisor, Salesforce
- **Critical finding:** API access is not included in base license. GCS must enable it. No public developer portal, no sandbox, no self-serve API key generation.
- Implementation cost range: 0,000-0,000 for medium businesses with 1-2 month timeline; enterprise runs 00,000-00,000 over 3-6 months
- **No native webhooks confirmed.** A2000 describes real-time data but this appears to be internal polling within their ecosystem, not outbound webhooks to third-party systems.
- Sunrise Integration is an official A2000 partner, but their published documentation does not specifically cover A2000 -- work is done by direct consultation only.

**Source:** [A2000 -- Capterra Reviews](https://www.capterra.com/p/140356/A2000-Software/), [Sunrise Integration -- A2000](https://www.sunriseintegration.com/a2000), [Hara Partners -- A2000](https://www.harapartners.com/partners/a2000-global-commerce-solutions/), [A2000 FAQ](https://a2000software.com/faqs/)

### EDI Module

A2000 native EDI module ships with 500+ pre-built trading partner maps. The EDI 850 import route (Hermes Tier 2) is the lowest-friction integration path -- no GCS vendor engagement required beyond confirming the EDI module is licensed. Module covers: 850, 855, 856, 810, 820, 832, 846, 997. This also directly aligns with Walgreens native workflow.

### Practical Integration Priority for Hermes Phase 0

1. **Tier 1 (REST API):** Emmanuel calls GCS directly -- Is the API included in my license? Can you send the endpoint documentation? Expect 1-2 week response.
2. **Tier 2 (EDI 850 import):** Confirm A2000 EDI module is active on the license. Map fields once; runs automatically. Best long-term path regardless of REST API availability.
3. **Tier 4 (Playwright):** Valid for demo/MVP even if Tier 1/2 unavailable at launch. Not a permanent solution for ASN compliance -- screen automation cannot generate SSCC labels or transmit EDI.

---

## 4. Common Wholesale Automation Pitfalls

### What Goes Wrong When Small Wholesalers Automate PO Entry

**Format fragmentation is worse than expected.** Even a single buyer like Walgreens sends POs in multiple formats: EDI 850 for standard re-orders, PDF for seasonal orders, Excel via SupplierNet for special programs. A system handling only one format breaks when the buyer changes workflow.

**The PO is not the ground truth -- the ASN is.** Automation teams focus on PO entry, but chargebacks happen at shipment time. Building half the loop without the compliance layer creates more liability exposure, not less -- orders move faster through the system while the compliance checks are not yet built.

**Data quality in = garbage decisions out.** Manual PO error rate is 3-5% on multi-line documents. AI parser accuracy on standard PDFs can reach 95%+, but apparel-specific attributes -- style number, colorway code, size scale -- are abbreviated inconsistently across buyers. The SKU mapping table is a maintenance burden, not a one-time setup.

**A2000 validation fires after entry, not before.** If Hermes enters an order with a pricing mismatch or invalid SKU, A2000 may accept the record but flag it internally as an exception. Hermes must check A2000 response codes for actual processing status -- not just whether the HTTP call returned 200.

**Credit state is not static.** A buyer can hit their credit limit mid-day. Auto-entering POs without checking credit creates orders A2000 flags for internal hold while Hermes reports success. The operator finds out days later when the buyer calls asking where their shipment is.

### Real Cost of Chargebacks vs. Cost of Automation

| Item | Cost |
|---|---|
| Typical chargeback penalty per incident | 0-00 flat, or 1%-5% of gross invoice |
| Late ASN fine at Walgreens | Up to 5% of invoice value per the Cost Recovery Program formula |
| Annual chargeback exposure at small wholesaler | 0,000-50,000/year for manual-entry operations |
| Industry-wide annual chargebacks | .5B+ |
| Manual PO entry error rate | 3-5% per line item |
| Full EDI compliance stack (VAN + middleware) | 00-,000/month depending on volume and provider |
| Single transposed SKU on a 150-line PO | Potential chargeback wiping the entire margin on that order |

**Source:** [OrderSync -- EDI for Wholesale](https://ordersync.io/edi-for/wholesale-distribution), [Shipfusion -- Avoid Retailer Chargebacks](https://www.shipfusion.com/blog/retailer-chargebacks), [JASCI Cloud](https://www.jascicloud.com/blog/retail-compliance-labels-guide), [Bold VAN -- Why Retailers Impose Chargeback Fees](https://www.boldvan.com/blog/supply-chain-management-why-retailers-impose-chargeback-fees)

### Why AI-for-Wholesale Automation Fails

The pattern across the research is consistent: products built against clean demo environments hit real-world ERP integration complexity.

- Over-reliance on API access that does not exist. ERPs like A2000 are Oracle-backed, vendor-gated, and built in the 1990s-2000s. The REST API on the website often means we have one if you are a 0K/yr enterprise customer.
- Ignoring the compliance layer. PO entry is easy. Chargebacks come from ASN, label, and routing guide compliance -- which requires integrating not just with the ERP but with the carrier, the label printer, and the VAN.
- Solving for speed, not accuracy. Faster wrong entries are worse than slower correct ones. AI speed is useless if the SKU match rate is 85% and the remaining 15% creates compliance violations.
- No chargeback recovery workflow. Systems that get orders in but do not track dispute windows leave money permanently on the table after the 4-week window closes.

---

## 5. Wholesale Pricing Complexity

The price on a Walgreens PO is the end result of a multi-layer agreement stack. A pricing mismatch at any layer triggers either an 855 change (vendor must fix before shipping) or a deduction on the 820 remittance (Walgreens takes money back unilaterally, often 30-60 days after the fact).

### Price Structure Layers

| Layer | Description | Who Controls It |
|---|---|---|
| List Price / MSRP | Published suggested retail price | Vendor |
| Wholesale / Net Price | The actual price vendor charges Walgreens. Negotiated at account level. | Buyer negotiation |
| Cost-Plus | COGS + overhead + target margin = wholesale price | Vendor calculation |
| Retail-Minus (Keystone) | Retailer works backward from planned retail and tells vendor what they will pay | Walgreens buyer |
| Contract Pricing | Account-specific locked price overriding list for this customer | Agreed contract |
| Volume Tier | Price breaks at quantity thresholds (e.g., 100-499 units = ; 500+ = ) | Vendor price list |
| Promotional Pricing | Time-limited price reduction for a campaign or seasonal push | Co-agreed |
| MDF / Co-op Allowance | Vendor contributes 1-5% of invoice value to fund joint marketing; often deducted on 820 | Walgreens program |
| Slotting Fee | One-time fee for shelf placement on new item launches. Walgreens charges these; specific amounts not publicly disclosed | Walgreens buyer |
| Volume Rebate | Backend discount paid by vendor to Walgreens after period-end based on total purchased volume | Annual program |
| Chargeback Deduction | Walgreens takes money back from invoices for compliance violations | Walgreens unilaterally |

The price Hermes needs to validate on a PO is: contract price with volume tier applied, after promo codes, before MDF deduction. If A2000 holds the contract price table, validation is a lookup per line item. If a PO arrives with a promotional price not yet configured in A2000, validation fails even though the price is technically correct -- Hermes must distinguish a genuine mismatch from a missing price table entry.

In A2000-class systems: customer-specific price lists override base list prices; volume break tables apply quantity-triggered changes; promotional prices are time-bounded overrides. The ERP governs all of this; humans maintain the tables; agents validate against them.

**Source:** [Qoblex -- Wholesale Pricing Guide](https://qoblex.com/learning-center/guide-to-wholesale-pricing/), [Zoey -- Multiple Price List Problem](https://www.zoey.com/how-distributors-are-solving-the-multiple-price-list-problem/), [360insights -- MDF and Co-op Explained](https://www.360insights.com/blog/market-development-funds-101-mdf-and-co-op-explained), [Endless Commerce -- Wholesale Price Lists](https://endlesscommerce.com/playbook/wholesale-price-lists-and-terms/)

---

## 6. Apparel-Specific Complexity That Generic Wholesale Systems Miss

This is the domain where A2000 was purpose-built and where generic automation fails completely.

### Size Scale and Color Matrix

A single apparel style generates a matrix of SKUs:
- 1 style x 6 colors x 8 sizes = 48 distinct SKUs
- 100-style seasonal collection = ~5,000 SKUs
- 200-style full collection = 11,000+ active SKUs

A Walgreens PO for apparel items does not say order 500 units of item 12345. It says:



That is 780 individual order lines collapsed into a size-color matrix. The PO parser must understand size scale notation, which varies by buyer: XS vs. 0 vs. 32 depending on product category and buyer convention. A2000 order entry must explode the matrix into individual SKU-level lines.

### Season Codes and Style Cross-Reference

Apparel orders reference:
- **Style number** -- vendor-internal (e.g., BT-2210)
- **Season code** -- e.g., SP26 (Spring 2026), FA26 (Fall 2026)
- **Colorway code** -- often a 3-letter code like NVY, not hex or RGB
- **Buyer item number** -- Walgreens has internal item codes that must cross-reference to vendor style numbers

The cross-reference table between Walgreens item codes and vendor style numbers is a separate data layer that must be maintained in A2000. A new style launch without an updated cross-reference table causes every parser extraction to fail silently.

### Apparel-Specific Requirements for Any PO Automation

| Requirement | Why It Matters |
|---|---|
| Size scale matrix expansion | PO arrives as matrix; A2000 needs individual SKU-level line items |
| Colorway code normalization | NVY = Navy = the correct internal code -- parser needs a lookup table, not inference |
| Season code validation | Cannot enter an order against a closed season in A2000 |
| Buyer item number to vendor style mapping | Mandatory for Walgreens orders |
| UPC/EAN per SKU variant | Each size-color combination needs a unique barcode for GS1-128 label compliance |
| Size-level inventory allocation | Cannot allocate smalls from a pool of larges -- inventory is SKU-specific at size level |

**Source:** [ECOSIRE -- ERP for Textile and Apparel](https://ecosire.com/blog/erp-for-textile-industry), [AIMS360 -- Apparel Inventory Management](https://www.aims360.com/education/apparel-inventory-management-software-erp-guide), [Gestisoft -- Apparel ERP Guide](https://www.gestisoft.com/en/blog/apparel-erp), [NetSuite -- Fashion ERP](https://www.netsuite.com/portal/resource/articles/erp/erp-implementation-fashion.shtml)

---

## Implications for Hermes -- 10 Gaps, Ranked by Severity

| # | Gap | What Is Missing Now | Severity |
|---|---|---|---|
| 1 | ASN Generation and Transmission (EDI 856) | Hermes stops at invoice delivery. No ASN = automatic Walgreens chargeback on every shipment. Not an enhancement -- a pre-condition for not making the vendor compliance situation actively worse. | MUST FIX PRE-LAUNCH |
| 2 | EDI 855 PO Acknowledgment | Hermes does not send an 855 back to Walgreens after PO receipt. Walgreens EDI compliance requires this within 24-48 hours. Missing it flags the vendor in Walgreens system before the first box ships. | MUST FIX PRE-LAUNCH |
| 3 | Pricing Validation Against Contract | Current model performs no price check on ingestion. A PO with incorrect pricing gets entered silently. Walgreens deducts the difference on the 820 remittance -- often 30-60 days later. Emmanuel finds out when the bank balance is short with no paper trail. | MUST FIX PRE-LAUNCH |
| 4 | GS1-128 / SSCC Carton Label Generation | No label printing in current design. Carton labels must be printed before the truck departs. SSCC data must match the ASN exactly. Requires integration with a label printer or a purpose-built label generation module outputting ZPL or PDF for thermal printing. | MUST FIX PRE-LAUNCH |
| 5 | Credit Hold Check Before Order Entry | Hermes will enter POs from buyers over their credit limit without checking. Creates orders A2000 flags for internal hold while Hermes reports success. Operator discovers the problem days later when the buyer calls asking where their shipment is. | MUST FIX PRE-LAUNCH |
| 6 | Size/Color Matrix Parsing (Apparel-Specific) | If Emmanuel sells apparel to Walgreens, POs arrive as matrices, not flat item lists. Current parser spec does not address this. Parsing failure means bad order entry or manual intervention required for every apparel PO -- defeating the purpose of the system. | MUST FIX PRE-LAUNCH (if apparel inventory) |
| 7 | Chargeback Dispute Tracking and Alerting | Walgreens has a 4-week dispute window. No system currently tracks chargeback notifications, investigates them against EDI records, and alerts before the window closes. Money is permanently forfeited after 4 weeks. | MUST FIX BEFORE SECOND CLIENT |
| 8 | EDI 820 Remittance Parsing | When Walgreens pays, the 820 lists which invoices are paid and which deductions are taken. Hermes has no mechanism to receive or parse this. Emmanuel cannot reconcile paid invoices vs. disputable deductions without manually reading each 820 file. | MUST FIX BEFORE SECOND CLIENT |
| 9 | Partial Ship / Backorder Decision Logic | Current model assumes complete fulfillment on every PO. Real scenario: 80% in stock, 20% backordered. Does Hermes ship partial and send a partial ASN plus partial invoice, or hold the order? This requires a configurable business rule layer. | MUST FIX BEFORE SECOND CLIENT |
| 10 | Returns / RGA Workflow | When Walgreens returns merchandise, they issue a debit memo. No RGA workflow exists in Hermes -- no way to receive return authorization, process credit memo in A2000, and reconcile the deduction on the next 820. | FUTURE FEATURE (Phase 5+) |

---

## Summary Assessment

The current Hermes Phase 1-4 design automates the easy part of wholesale order processing -- PO ingestion and order entry -- while leaving the compliance surface almost entirely exposed. For a vendor shipping to Walgreens specifically, gaps #1 through #5 are not optional improvements; they are pre-conditions for the system not making the vendor chargeback situation worse than before automation.

The core architectural insight missing from the current design: **the critical compliance moment in wholesale distribution is not when the PO arrives. It is when the truck leaves the dock.** The ASN, the carton labels, and the routing guide compliance all happen in the 30-minute window before departure. That is where Hermes Phase 2 must expand.

Recommended immediate action for scope discussion with Emmanuel: confirm whether Phase 2 (POS Integration) can be extended to include ASN generation and label output as Phase 2b. These are not large features individually -- but they are blocking features for Walgreens compliance, and they are the difference between a system that saves money and one that silently generates fines while the operator thinks everything is running smoothly.

---

*Research conducted April 2026. All claims cited to primary sources. EDI transaction set specifications per ANSI X12 Version 5010 unless otherwise noted.*
