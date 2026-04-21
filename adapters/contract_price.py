"""Customer contract price lookup and PO pricing validation.

Implements Phase 4b — Pricing & Credit Validation (PRE-LAUNCH).

A pricing mismatch on a Walgreens PO does not produce an immediate error —
A2000 may accept the order, but Walgreens will take the difference back as a
deduction on the 820 remittance 30–60 days later. Emmanuel finds out when the
bank balance is short with no paper trail.

This module validates every PO line item against the A2000 contract price table
before order entry. Mismatches are surfaced via EDI 855 Accept-with-Changes rather
than entered silently.

Price layers handled (per WHOLESALE_RESEARCH.md Section 5):
  - Contract price (account-specific override of list price)
  - Volume tier (quantity breaks)
  - Promotional pricing (time-bounded overrides)

Reference: docs/WHOLESALE_RESEARCH.md — Section 5 (Wholesale Pricing Complexity),
           lifecycle Stage 4 (Pricing Validation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from adapters.po_parser import POData


@dataclass
class PricingMismatch:
    """A single line item where the PO price does not match the contract price.

    Attributes
    ----------
    line_seq:
        PO line sequence number (1-indexed).
    sku:
        Vendor or buyer SKU as it appears on the PO line.
    po_price:
        Price as stated on the incoming PO.
    contract_price:
        Price from the A2000 contract table for this customer and SKU.
    quantity:
        Ordered quantity (relevant for volume tier edge cases).
    mismatch_type:
        Category of mismatch:
        - "price_below"   — PO price is below contract (Walgreens is under-paying)
        - "price_above"   — PO price is above contract (rare; flag for review)
        - "no_contract"   — No contract record found for this SKU + customer combo
        - "promo_missing" — PO references a promo price not yet in A2000
    """

    line_seq: int
    sku: str
    po_price: Decimal
    contract_price: Decimal
    quantity: int
    mismatch_type: str


class ContractPriceTable:
    """In-memory cache of A2000 customer-specific contract prices.

    Loaded once per order cycle from the A2000 API or EDI 832 Price/Sales Catalog.
    Handles volume tiers and promotional windows.

    Usage::

        table = ContractPriceTable.load_from_a2000(customer_id="WBA", a2000_client=client)
        price = table.lookup("SKU-001", quantity=500, order_date=date.today())
    """

    def __init__(self) -> None:
        raise NotImplementedError("Phase 4b — see docs/BUILD_PLAN.md")

    @classmethod
    def load_from_a2000(
        cls,
        customer_id: str,
        a2000_client,  # A2000ClientBase — typed as Any to avoid circular import
    ) -> "ContractPriceTable":
        """Load price records for a customer from A2000 and return a populated table.

        Parameters
        ----------
        customer_id:
            A2000 customer account code (e.g. Walgreens account ID).
        a2000_client:
            Live A2000 client instance (any tier — API, EDI, or mock).

        Returns
        -------
        ContractPriceTable
            Populated price table ready for lookup calls.

        Raises
        ------
        NotImplementedError
            Until Phase 4b implementation is complete.
        """
        raise NotImplementedError("Phase 4b — see docs/BUILD_PLAN.md")


def lookup_price(
    customer_id: str,
    sku: str,
    quantity: int,
    order_date: date,
    table: ContractPriceTable,
) -> Decimal:
    """Return the effective contract price for a SKU at a given quantity and date.

    Applies volume tier logic (quantity thresholds → price breaks) and
    promotional window overrides before returning the final price.

    Parameters
    ----------
    customer_id:
        A2000 customer account code.
    sku:
        Vendor item code as stored in A2000.
    quantity:
        Ordered quantity — used to apply volume tier pricing.
    order_date:
        Date of the PO — used to validate promotional price windows.
    table:
        Populated :class:`ContractPriceTable` instance.

    Returns
    -------
    Decimal
        Effective price per unit at the given quantity and date.

    Raises
    ------
    KeyError
        If no price record exists for this customer + SKU combination.
    NotImplementedError
        Until Phase 4b implementation is complete.
    """
    raise NotImplementedError("Phase 4b — see docs/BUILD_PLAN.md")


def validate_po_pricing(
    po: POData,
    table: ContractPriceTable,
) -> list[PricingMismatch]:
    """Validate all line items on a PO against the contract price table.

    Parameters
    ----------
    po:
        Parsed purchase order to validate.
    table:
        Contract price table for the PO's customer.

    Returns
    -------
    list[PricingMismatch]
        Empty list if all prices match. Each entry is a line item where the
        PO price diverges from the contract price or no contract record exists.
        Caller passes this list to :func:`~adapters.edi_855_ack.generate_855`
        with mode="change" to transmit corrections back to Walgreens.

    Raises
    ------
    NotImplementedError
        Until Phase 4b implementation is complete.
    """
    raise NotImplementedError("Phase 4b — see docs/BUILD_PLAN.md")
