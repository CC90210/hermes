"""EDI 820 Remittance Advice parser.

Implements Phase 6b — Remittance Reconciliation (Pre-Second-Client).

When Walgreens pays, the EDI 820 tells the vendor exactly which invoices are
paid and which deductions have been taken. Without parsing this document,
Emmanuel reconciles payment manually — and deductions land silently in the
bank balance with no actionable detail attached.

This module parses the 820, matches payments to open invoices, and surfaces
deductions for chargeback_tracker.py to act on within the 4-week dispute window.

Reference: docs/WHOLESALE_RESEARCH.md — Section 1 (lifecycle Stage 15, Payment
           Remittance) and Stage 16 (Deduction Resolution).
ANSI X12 Version 5010, Transaction Set 820.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


@dataclass
class Deduction:
    """A single deduction line item taken by Walgreens on a remittance.

    Attributes
    ----------
    type:
        Category of deduction as reported in the 820 reason code segment:
        - "MDF"        — Marketing Development Fund / co-op contribution
        - "chargeback" — Compliance violation penalty (ASN, label, etc.)
        - "allowance"  — Volume or promotional allowance applied
    amount:
        Dollar value of the deduction (always positive; represents money taken).
    reason_code:
        X12 reason code string from the BPR/RMR/REF segments (e.g. "AK", "AU").
    invoice_ref:
        Invoice number this deduction is applied against, as reported by Walgreens.
    deduction_id:
        Walgreens internal deduction reference number for use in dispute
        submissions. Sourced from the REF segment with qualifier "TJ" or "CN".
    description:
        Free-text description from the NTE segment, if present.
    """

    type: Literal["MDF", "chargeback", "allowance"]
    amount: Decimal
    reason_code: str
    invoice_ref: str
    deduction_id: str = ""
    description: str = ""


@dataclass
class RemittanceAdvice:
    """Parsed representation of a single EDI 820 Remittance Advice document.

    Attributes
    ----------
    payment_amount:
        Net amount actually paid (gross invoiced minus all deductions).
    check_number:
        ACH trace number or check number as reported in the BPR segment.
    payment_date:
        ISO-8601 date the payment was issued (from BPR09).
    payer_name:
        Walgreens entity name as reported in the N1*PE segment.
    invoices_paid:
        List of invoice numbers covered by this remittance (fully paid).
    deductions:
        All deduction line items; may be empty if payment is clean.
    """

    payment_amount: Decimal
    check_number: str
    payment_date: str
    payer_name: str
    invoices_paid: list[str] = field(default_factory=list)
    deductions: list[Deduction] = field(default_factory=list)


def parse_820(edi_bytes: bytes) -> RemittanceAdvice:
    """Parse a raw EDI X12 820 document into a structured RemittanceAdvice.

    Handles ANSI X12 5010 envelope structure (ISA/GS/ST/BPR/TRN/DTM/N1/RMR/REF/NTE).
    Element delimiters and segment terminators are read from the ISA header rather
    than assumed — different VANs use different separators.

    Parameters
    ----------
    edi_bytes:
        Raw EDI 820 document bytes as received from the VAN or AS2 endpoint.

    Returns
    -------
    RemittanceAdvice
        Fully populated remittance structure with all deductions extracted.

    Raises
    ------
    ValueError
        If the document is not a valid 820 transaction set, or mandatory BPR
        segments are missing.
    NotImplementedError
        Until Phase 6b implementation is complete.
    """
    raise NotImplementedError("Phase 6b — see docs/BUILD_PLAN.md")
