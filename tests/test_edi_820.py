"""Tests for adapters/edi_820_remit.py — EDI 820 Remittance Advice parser."""

from __future__ import annotations

from decimal import Decimal

import pytest

from adapters.edi_820_remit import (
    DeductionType,
    RemittanceAdvice,
    classify_deduction,
    extract_dispute_candidates,
    parse_820,
)


# ---------------------------------------------------------------------------
# EDI 820 fixture builder
# ---------------------------------------------------------------------------

def _build_820(
    trn: str = "TRN-001",
    payment_amount: str = "1000.00",
    payment_date: str = "20260415",
    remitter: str = "Walgreens",
    invoices: list[dict] | None = None,
) -> bytes:
    """Build a minimal but structurally valid X12 5010 820 document."""
    e = "*"    # element separator
    s = "~\n"  # segment terminator

    isa = (
        f"ISA{e}00{e}          {e}00{e}          "
        f"{e}ZZ{e}WALGREENS      {e}ZZ{e}VENDOR         "
        f"{e}260415{e}1200{e}^{e}00501{e}000000001{e}0{e}P{e}>"
    )

    lines: list[str] = [
        isa,
        f"GS{e}RA{e}WALGREENS{e}VENDOR{e}20260415{e}1200{e}1{e}X{e}005010",
        f"ST{e}820{e}0001",
        f"BPR{e}I{e}{payment_amount}{e}C{e}ACH{e}{e}{e}{e}{e}{e}{e}{e}{e}{e}{e}{e}{e}{payment_date}",
        f"TRN{e}1{e}{trn}",
        f"DTM{e}097{e}{payment_date}",
        f"N1{e}PE{e}{remitter}",
    ]

    for inv in (invoices or []):
        inv_num = inv.get("invoice_number", "INV-001")
        inv_amt = inv.get("invoice_amount", payment_amount)
        paid_amt = inv.get("paid_amount", payment_amount)
        lines.append(f"ENT{e}1")
        lines.append(f"RMR{e}IV{e}{inv_num}{e}PI{e}{paid_amt}{e}{inv_amt}")
        for ded in inv.get("deductions", []):
            code = ded.get("code", "CB")
            amount = ded.get("amount", "50.00")
            desc = ded.get("desc", "")
            lines.append(f"ADX{e}{amount}{e}{code}{e}{desc}")

    total_segs = len(lines) - 3  # ISA, GS, ST overhead
    lines.append(f"SE{e}{total_segs + 1}{e}0001")
    lines.append(f"GE{e}1{e}1")
    lines.append(f"IEA{e}1{e}000000001")

    raw = s.join(lines) + s
    return raw.encode("ascii")


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

def test_parse_820_simple_no_deductions() -> None:
    """Parse a clean 820 with one invoice, no deductions."""
    edi = _build_820(
        trn="TRN-CLEAN",
        payment_amount="500.00",
        invoices=[{"invoice_number": "INV-2026-001", "invoice_amount": "500.00", "paid_amount": "500.00"}],
    )
    remit = parse_820(edi)
    assert remit.trn_number == "TRN-CLEAN"
    assert remit.total_payment_amount == Decimal("500.00")
    assert remit.remitter_name == "Walgreens"
    assert len(remit.invoices_paid) == 1
    assert remit.invoices_paid[0].invoice_number == "INV-2026-001"
    assert remit.invoices_paid[0].deductions == []


def test_parse_820_payment_date() -> None:
    edi = _build_820(payment_date="20260401")
    remit = parse_820(edi)
    assert remit.payment_date.year == 2026
    assert remit.payment_date.month == 4
    assert remit.payment_date.day == 1


def test_parse_820_with_chargeback() -> None:
    """820 with one chargeback deduction is parsed correctly."""
    edi = _build_820(
        payment_amount="450.00",
        invoices=[{
            "invoice_number": "INV-100",
            "invoice_amount": "500.00",
            "paid_amount": "450.00",
            "deductions": [{"code": "CB", "amount": "50.00", "desc": "Compliance violation"}],
        }],
    )
    remit = parse_820(edi)
    assert len(remit.invoices_paid) == 1
    inv = remit.invoices_paid[0]
    assert len(inv.deductions) == 1
    ded = inv.deductions[0]
    assert ded.type == DeductionType.CHARGEBACK
    assert ded.amount == Decimal("50.00")
    assert ded.invoice_ref == "INV-100"


def test_parse_820_multiple_deduction_types() -> None:
    edi = _build_820(
        payment_amount="370.00",
        invoices=[{
            "invoice_number": "INV-200",
            "invoice_amount": "500.00",
            "paid_amount": "370.00",
            "deductions": [
                {"code": "CB", "amount": "80.00"},
                {"code": "MA", "amount": "25.00"},
                {"code": "AJ", "amount": "25.00"},
            ],
        }],
    )
    remit = parse_820(edi)
    inv = remit.invoices_paid[0]
    assert len(inv.deductions) == 3
    types = {d.type for d in inv.deductions}
    assert DeductionType.CHARGEBACK in types
    assert DeductionType.MDF in types
    assert DeductionType.ALLOWANCE in types


def test_parse_820_total_deductions_property() -> None:
    edi = _build_820(
        invoices=[{
            "invoice_number": "INV-300",
            "invoice_amount": "1000.00",
            "paid_amount": "900.00",
            "deductions": [
                {"code": "CB", "amount": "60.00"},
                {"code": "AJ", "amount": "40.00"},
            ],
        }],
    )
    remit = parse_820(edi)
    assert remit.total_deductions == Decimal("100.00")


def test_parse_820_invalid_transaction_set_raises() -> None:
    """Document with wrong ST transaction set must raise ValueError."""
    edi = _build_820()
    # Corrupt the ST segment to be 850 instead of 820
    broken = edi.replace(b"ST*820*", b"ST*850*")
    with pytest.raises(ValueError, match="820"):
        parse_820(broken)


def test_parse_820_too_short_raises() -> None:
    with pytest.raises(ValueError, match="short"):
        parse_820(b"ISA*short")


# ---------------------------------------------------------------------------
# classify_deduction
# ---------------------------------------------------------------------------

def test_classify_known_code_cb() -> None:
    assert classify_deduction("CB") == DeductionType.CHARGEBACK


def test_classify_known_code_ma() -> None:
    assert classify_deduction("MA") == DeductionType.MDF


def test_classify_known_code_aj() -> None:
    assert classify_deduction("AJ") == DeductionType.ALLOWANCE


def test_classify_known_code_sk() -> None:
    assert classify_deduction("SK") == DeductionType.SHORT_SHIP


def test_classify_unknown_code_returns_unknown() -> None:
    assert classify_deduction("ZZ") == DeductionType.UNKNOWN


def test_classify_unknown_code_description_fallback() -> None:
    """Unknown reason code but known keyword in description → correct type."""
    assert classify_deduction("XX", "Compliance chargeback for late ASN") == DeductionType.CHARGEBACK


# ---------------------------------------------------------------------------
# extract_dispute_candidates
# ---------------------------------------------------------------------------

def test_extract_dispute_candidates_filters_allowances() -> None:
    """Allowances are not disputable; chargebacks are."""
    from adapters.edi_820_remit import Deduction, InvoicePayment

    remit = RemittanceAdvice(
        trn_number="T1",
        payment_date=__import__("datetime").date(2026, 4, 1),
        total_payment_amount=Decimal("900"),
        remitter_name="Walgreens",
        invoices_paid=[
            InvoicePayment(
                invoice_number="INV-1",
                invoice_amount=Decimal("1000"),
                paid_amount=Decimal("900"),
                deductions=[
                    Deduction(type=DeductionType.CHARGEBACK, amount=Decimal("50"), reason_code="CB", invoice_ref="INV-1", dispute_eligible=True),
                    Deduction(type=DeductionType.ALLOWANCE, amount=Decimal("50"), reason_code="AJ", invoice_ref="INV-1", dispute_eligible=False),
                ],
            )
        ],
    )
    candidates = extract_dispute_candidates(remit)
    assert len(candidates) == 1
    assert candidates[0].type == DeductionType.CHARGEBACK


def test_extract_dispute_candidates_empty_when_no_disputes() -> None:
    from adapters.edi_820_remit import Deduction, InvoicePayment

    remit = RemittanceAdvice(
        trn_number="T2",
        payment_date=__import__("datetime").date(2026, 4, 1),
        total_payment_amount=Decimal("500"),
        remitter_name="Walgreens",
        invoices_paid=[
            InvoicePayment(
                invoice_number="INV-2",
                invoice_amount=Decimal("500"),
                paid_amount=Decimal("450"),
                deductions=[
                    Deduction(type=DeductionType.ALLOWANCE, amount=Decimal("50"), reason_code="AU", invoice_ref="INV-2", dispute_eligible=False),
                ],
            )
        ],
    )
    assert extract_dispute_candidates(remit) == []
