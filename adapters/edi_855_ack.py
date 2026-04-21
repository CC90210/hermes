"""EDI 855 Purchase Order Acknowledgment generator.

Implements Phase 3b — PO Acknowledgment (PRE-LAUNCH).

Walgreens requires an EDI 855 response within 24–48 hours of every 850 PO receipt.
Missing this window flags the vendor in Walgreens' compliance system before the first
shipment ever leaves the dock.

Three response modes:
  - accept: clean PO, all line items confirmed at PO price/qty/date
  - change: accept with modifications (price, quantity, or ship-date adjustments)
  - reject: invalid SKU, customer on credit hold, or structurally unprocessable PO

Transmission target is the trading partner's AS2 endpoint or VAN mailbox as configured
during Phase 0 discovery.

Reference: docs/WHOLESALE_RESEARCH.md — Section 2 (Walgreens Vendor Compliance),
           lifecycle Stage 3 (PO Acknowledgment).
ANSI X12 Version 5010, Transaction Set 855.
"""

from __future__ import annotations

from typing import Literal

from adapters.po_parser import POData


def generate_855(
    po: POData,
    mode: Literal["accept", "change", "reject"],
    changes: dict | None = None,
) -> bytes:
    """Generate an ANSI X12 5010 EDI 855 PO Acknowledgment.

    Parameters
    ----------
    po:
        The original parsed purchase order being acknowledged.
    mode:
        Response disposition:
        - "accept"  — acknowledge all lines as-is (AC in BAK01 equivalent).
        - "change"  — acknowledge with modifications; ``changes`` must be provided.
        - "reject"  — reject the PO entirely with a reason code.
    changes:
        Required when mode="change". Shape::

            {
                "lines": [
                    {
                        "line_seq": 1,
                        "sku": "VENDOR-SKU-001",
                        "acknowledged_qty": 90,       # from original 100
                        "acknowledged_price": 12.50,  # corrected price
                        "ship_date": "2026-05-01",    # adjusted date
                    }
                ],
                "reject_reason": None,  # or a string when mode="reject"
            }

    Returns
    -------
    bytes
        Raw EDI X12 byte string ready for transmission. Envelope segments
        (ISA/GS/ST/SE/GE/IEA) are included.

    Raises
    ------
    ValueError
        If mode="change" but changes is None or empty.
    NotImplementedError
        Until Phase 3b implementation is complete.
    """
    raise NotImplementedError("Phase 3b — see docs/BUILD_PLAN.md")


def transmit_855(edi_bytes: bytes, va_target: str) -> bool:
    """Transmit a generated 855 document to the configured VAN or AS2 endpoint.

    Parameters
    ----------
    edi_bytes:
        Raw EDI X12 bytes as returned by :func:`generate_855`.
    va_target:
        Interchange qualifier + ID identifying the trading partner's mailbox,
        e.g. ``"01:0000000000"`` for a standard ISA06 target, or an AS2 station ID.

    Returns
    -------
    bool
        True if the VAN/AS2 endpoint confirmed receipt; False on transmission
        failure (caller should retry and escalate after 3 attempts).

    Raises
    ------
    NotImplementedError
        Until Phase 3b implementation is complete.
    """
    raise NotImplementedError("Phase 3b — see docs/BUILD_PLAN.md")
