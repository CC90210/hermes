"""EDI 820 Remittance Advice parser.

Implements Phase 6b — Remittance Reconciliation (Pre-Second-Client).

When Walgreens pays, the EDI 820 tells the vendor exactly which invoices are
paid and which deductions have been taken. Without parsing this document,
Emmanuel reconciles payment manually — and deductions land silently in the
bank balance with no actionable detail attached.

Reference: docs/WHOLESALE_RESEARCH.md — Section 1 (lifecycle Stage 15, Payment
           Remittance) and Stage 16 (Deduction Resolution).
ANSI X12 Version 5010, Transaction Set 820.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

_log = logging.getLogger(__name__)


class DeductionType(str, Enum):
    CHARGEBACK = "chargeback"
    MDF = "mdf"
    SLOTTING_FEE = "slotting"
    ALLOWANCE = "allowance"
    VOLUME_REBATE = "volume_rebate"
    DAMAGE = "damage"
    SHORT_SHIP = "short_ship"
    LATE_ASN = "late_asn"
    WRONG_LABEL = "wrong_label"
    UNKNOWN = "unknown"


@dataclass
class Deduction:
    type: DeductionType
    amount: Decimal
    reason_code: str
    invoice_ref: str
    description: str = ""
    dispute_eligible: bool = True


@dataclass
class InvoicePayment:
    invoice_number: str
    invoice_amount: Decimal
    paid_amount: Decimal
    deductions: list[Deduction] = field(default_factory=list)


@dataclass
class RemittanceAdvice:
    trn_number: str
    payment_date: date
    total_payment_amount: Decimal
    remitter_name: str
    invoices_paid: list[InvoicePayment] = field(default_factory=list)

    @property
    def total_deductions(self) -> Decimal:
        return sum(
            (d.amount for inv in self.invoices_paid for d in inv.deductions),
            Decimal("0"),
        )


# ---------------------------------------------------------------------------
# Reason code map — extend as real 820s are encountered
# ---------------------------------------------------------------------------

_DEDUCTION_REASON_MAP: dict[str, DeductionType] = {
    "CB": DeductionType.CHARGEBACK,
    "CO": DeductionType.CHARGEBACK,   # Compliance fine
    "CF": DeductionType.CHARGEBACK,   # Compliance fine variant
    "MA": DeductionType.MDF,
    "MF": DeductionType.MDF,
    "SF": DeductionType.SLOTTING_FEE,
    "AJ": DeductionType.ALLOWANCE,
    "AU": DeductionType.ALLOWANCE,
    "52": DeductionType.ALLOWANCE,    # ANSI general adjustment
    "RA": DeductionType.VOLUME_REBATE,
    "VR": DeductionType.VOLUME_REBATE,
    "DM": DeductionType.DAMAGE,
    "DA": DeductionType.DAMAGE,
    "SK": DeductionType.SHORT_SHIP,
    "SS": DeductionType.SHORT_SHIP,
    "LA": DeductionType.LATE_ASN,
    "WL": DeductionType.WRONG_LABEL,
}

# Deduction types that can be disputed
_DISPUTABLE_TYPES: frozenset[DeductionType] = frozenset({
    DeductionType.CHARGEBACK,
    DeductionType.LATE_ASN,
    DeductionType.WRONG_LABEL,
    DeductionType.SHORT_SHIP,
    DeductionType.DAMAGE,
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_820(edi_bytes: bytes) -> RemittanceAdvice:
    """Parse a complete X12 5010 820 document.

    Returns a RemittanceAdvice with all invoices and their deductions identified.
    """
    raw = edi_bytes.decode("utf-8", errors="replace")

    if len(raw) < 106:
        raise ValueError("Document too short to contain a valid ISA envelope")

    element_sep = raw[3]
    segment_sep = raw[105]

    segments = [s.strip() for s in raw.split(segment_sep) if s.strip()]

    # Validate this is an 820
    st_found = False
    for seg in segments:
        els = seg.split(element_sep)
        if els[0].strip() == "ST":
            if len(els) < 2 or els[1].strip() != "820":
                raise ValueError(
                    f"Expected transaction set 820, got {els[1].strip() if len(els) > 1 else 'unknown'}"
                )
            st_found = True
            break
    if not st_found:
        raise ValueError("No ST segment found in document")

    trn_number = ""
    payment_date: Optional[date] = None
    total_payment = Decimal("0")
    remitter_name = ""
    invoices: list[InvoicePayment] = []

    current_invoice: Optional[InvoicePayment] = None
    current_deductions: list[Deduction] = []

    for seg in segments:
        els = seg.split(element_sep)
        tag = els[0].strip()

        if tag == "BPR":
            # BPR*02*AMOUNT*C*ACH*...
            amount_str = els[2].strip() if len(els) > 2 else "0"
            total_payment = _safe_decimal(amount_str)
            # BPR09 = payment date (YYYYMMDD)
            if len(els) > 16:
                payment_date = _parse_edi_date(els[16].strip())

        elif tag == "TRN":
            # TRN*1*TRACE_NUMBER
            trn_number = els[2].strip() if len(els) > 2 else ""

        elif tag == "DTM":
            # DTM*097*YYYYMMDD — payment date alternative location
            qualifier = els[1].strip() if len(els) > 1 else ""
            if qualifier in ("097", "002", "405") and payment_date is None:
                payment_date = _parse_edi_date(els[2].strip() if len(els) > 2 else "")

        elif tag == "N1":
            # N1*PE*PAYER NAME — PE = payer entity
            qualifier = els[1].strip() if len(els) > 1 else ""
            name = els[2].strip() if len(els) > 2 else ""
            if qualifier == "PE" and name:
                remitter_name = name

        elif tag == "ENT":
            # Start of per-invoice entity loop — flush current invoice
            if current_invoice is not None:
                current_invoice.deductions = current_deductions[:]
                invoices.append(current_invoice)
            current_invoice = None
            current_deductions = []

        elif tag == "RMR":
            # RMR*IV*INVOICE_NUMBER**PAID_AMOUNT*INVOICE_AMOUNT
            qualifier = els[1].strip() if len(els) > 1 else ""
            if qualifier in ("IV", "TH", "IA"):
                inv_num = els[2].strip() if len(els) > 2 else ""
                paid_str = els[4].strip() if len(els) > 4 else "0"
                inv_str = els[5].strip() if len(els) > 5 else paid_str
                if current_invoice is not None:
                    # Flush and start fresh if we already have one
                    current_invoice.deductions = current_deductions[:]
                    invoices.append(current_invoice)
                    current_deductions = []
                current_invoice = InvoicePayment(
                    invoice_number=inv_num,
                    invoice_amount=_safe_decimal(inv_str),
                    paid_amount=_safe_decimal(paid_str),
                )

        elif tag == "ADX":
            # ADX*AMOUNT*REASON_CODE*[DESCRIPTION]
            amount_str = els[1].strip() if len(els) > 1 else "0"
            reason_code = els[2].strip() if len(els) > 2 else ""
            description = els[3].strip() if len(els) > 3 else ""
            inv_ref = current_invoice.invoice_number if current_invoice else ""
            ded_type = classify_deduction(reason_code, description)
            deduction = Deduction(
                type=ded_type,
                amount=_safe_decimal(amount_str).copy_abs(),
                reason_code=reason_code,
                invoice_ref=inv_ref,
                description=description,
                dispute_eligible=ded_type in _DISPUTABLE_TYPES,
            )
            current_deductions.append(deduction)

        elif tag == "IT1":
            # Alternative: per-invoice detail line
            # IT1**QUANTITY*UOM*PRICE*...
            pass  # Quantities captured via RMR; IT1 used for unit-level detail

    # Flush last invoice
    if current_invoice is not None:
        current_invoice.deductions = current_deductions[:]
        invoices.append(current_invoice)

    if payment_date is None:
        payment_date = date.today()
        _log.warning("parse_820: no payment date found in document, defaulting to today")

    return RemittanceAdvice(
        trn_number=trn_number,
        payment_date=payment_date,
        total_payment_amount=total_payment,
        remitter_name=remitter_name,
        invoices_paid=invoices,
    )


def classify_deduction(reason_code: str, description: str = "") -> DeductionType:
    """Map an ADX reason code + optional description to our DeductionType enum."""
    mapped = _DEDUCTION_REASON_MAP.get(reason_code.upper().strip())
    if mapped is not None:
        return mapped

    # Keyword fallback on description
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ("chargeback", "compliance", "violation", "fine", "penalty")):
        return DeductionType.CHARGEBACK
    if any(kw in desc_lower for kw in ("mdf", "marketing", "co-op", "coop")):
        return DeductionType.MDF
    if any(kw in desc_lower for kw in ("slotting", "slot")):
        return DeductionType.SLOTTING_FEE
    if any(kw in desc_lower for kw in ("rebate", "volume")):
        return DeductionType.VOLUME_REBATE
    if any(kw in desc_lower for kw in ("damage", "defect")):
        return DeductionType.DAMAGE
    if any(kw in desc_lower for kw in ("short", "shortage")):
        return DeductionType.SHORT_SHIP
    if any(kw in desc_lower for kw in ("asn", "advance ship")):
        return DeductionType.LATE_ASN
    if any(kw in desc_lower for kw in ("label", "barcode", "ucc")):
        return DeductionType.WRONG_LABEL
    if any(kw in desc_lower for kw in ("allowance", "discount", "promo")):
        return DeductionType.ALLOWANCE

    return DeductionType.UNKNOWN


def extract_dispute_candidates(remit: RemittanceAdvice) -> list[Deduction]:
    """Return only deductions that are dispute-eligible."""
    return [
        d
        for inv in remit.invoices_paid
        for d in inv.deductions
        if d.dispute_eligible
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_decimal(value: str) -> Decimal:
    cleaned = re.sub(r"[^\d.\-]", "", value)
    if not cleaned or cleaned in (".", "-"):
        return Decimal("0")
    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


def _parse_edi_date(value: str) -> Optional[date]:
    value = value.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
