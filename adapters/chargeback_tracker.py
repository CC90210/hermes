"""Chargeback deduction detection, dispute window tracking, and auto-draft.

Implements Phase 7b — Chargeback Dispute Tracking (Pre-Second-Client).

Walgreens deducts chargebacks unilaterally from the 820 remittance. The vendor
has exactly 4 weeks from the notification email to file a dispute — after that,
the money is permanently forfeited with no appeal path.

At small wholesalers this tracking is entirely manual. Deductions get noticed when
the bank balance is short, by which point the dispute window may already be closed.

This module:
  1. Detects new chargeback deductions from a parsed 820 RemittanceAdvice.
  2. Computes the dispute window close date (28 days from detection).
  3. Tracks status progression (OPEN → UNDER_DISPUTE → CLOSED/REVERSED).
  4. Auto-drafts dispute submissions referencing ASN proof and POD.
  5. Escalates to Emmanuel before the window closes.

Alert thresholds (days remaining in 4-week window):
  - 14 days → initial alert email to operator
  -  7 days → urgent alert
  -  3 days → escalate to phone/WhatsApp notification

Reference: docs/WHOLESALE_RESEARCH.md — Section 2 (Chargeback Formula,
           4-week dispute window), Section 1 (lifecycle Stage 16,
           Deduction Resolution).
Dispute submission: SupplierNet > Forms > Vendor Dispute Form
Dispute email:      SupplyChain.Compliance@Walgreens.com
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from adapters.edi_820_remit import RemittanceAdvice


@dataclass
class ChargebackEvent:
    """A single tracked chargeback deduction with dispute window state.

    Attributes
    ----------
    deduction_id:
        Walgreens internal deduction reference from the 820 REF segment.
    type:
        Deduction category: "MDF", "chargeback", or "allowance".
    amount:
        Dollar value of the deduction.
    invoice_ref:
        Invoice number this deduction was applied against.
    detected_at:
        UTC timestamp when Hermes first saw this deduction in a parsed 820.
    dispute_window_closes_at:
        UTC timestamp 28 days after ``detected_at``. Money is permanently
        forfeited if a dispute is not filed before this time.
    status:
        Current dispute lifecycle state:
        - "OPEN"          — detected, no action taken yet
        - "UNDER_DISPUTE" — dispute filed with Walgreens, awaiting response
        - "CLOSED"        — Walgreens closed without reversal
        - "REVERSED"      — Walgreens reversed the deduction (money recovered)
    asn_reference:
        ASN shipment ID from the corresponding 856, used as supporting evidence.
    notes:
        Free-text operator notes added during manual review.
    """

    deduction_id: str
    type: str
    amount: float
    invoice_ref: str
    detected_at: datetime
    dispute_window_closes_at: datetime
    status: Literal["OPEN", "UNDER_DISPUTE", "CLOSED", "REVERSED"] = "OPEN"
    asn_reference: Optional[str] = None
    notes: str = ""


def track_deductions(remittance: RemittanceAdvice) -> list[ChargebackEvent]:
    """Extract chargeback-type deductions from a remittance and create tracking events.

    Only deductions with ``type == "chargeback"`` generate ChargebackEvents with
    a 28-day dispute window. MDF and allowance deductions are logged but not
    tracked for dispute (they are contractual, not disputable).

    Parameters
    ----------
    remittance:
        Parsed 820 remittance as returned by :func:`~adapters.edi_820_remit.parse_820`.

    Returns
    -------
    list[ChargebackEvent]
        One event per chargeback deduction. ``detected_at`` is set to UTC now.
        Empty list if the remittance contains no chargeback deductions.

    Raises
    ------
    NotImplementedError
        Until Phase 7b implementation is complete.
    """
    raise NotImplementedError("Phase 7b — see docs/BUILD_PLAN.md")


def days_until_window_closes(event: ChargebackEvent) -> int:
    """Return the number of whole days remaining before the dispute window closes.

    Parameters
    ----------
    event:
        A tracked :class:`ChargebackEvent` with a populated ``dispute_window_closes_at``.

    Returns
    -------
    int
        Days remaining. Returns 0 if the window has already closed (caller should
        log the loss but not attempt to file a dispute).

    Raises
    ------
    NotImplementedError
        Until Phase 7b implementation is complete.
    """
    raise NotImplementedError("Phase 7b — see docs/BUILD_PLAN.md")


def auto_draft_dispute(event: ChargebackEvent) -> str:
    """Draft a dispute submission email body for a chargeback event.

    The draft is addressed to SupplyChain.Compliance@Walgreens.com and
    references the dispute form on SupplierNet. It includes:
      - Deduction ID and invoice reference
      - Dollar amount disputed
      - ASN reference and shipment date (if available from ``event.asn_reference``)
      - Valid dispute grounds (Walgreens DC pushed appointment, or insufficient lead time)
      - Request for deduction reversal

    The returned string is the email body only (no headers). The operator
    reviews and sends via Outlook — Hermes never sends dispute correspondence
    without human approval.

    Parameters
    ----------
    event:
        The chargeback event being disputed.

    Returns
    -------
    str
        Plain-text email body ready for operator review and transmission.

    Raises
    ------
    NotImplementedError
        Until Phase 7b implementation is complete.
    """
    raise NotImplementedError("Phase 7b — see docs/BUILD_PLAN.md")
