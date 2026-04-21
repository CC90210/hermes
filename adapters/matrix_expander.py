"""Apparel size-color matrix PO expander.

Implements Phase 5b — Apparel Matrix Parser (PRE-LAUNCH if apparel SKUs present).

Walgreens apparel POs do not arrive as flat line items. A single style line
contains a size-color matrix — e.g., 6 colors × 8 sizes = 48 distinct SKUs
collapsed into one block. A generic PO parser silently produces wrong order
entries (missing sizes, collapsed quantities) that result in short-ship chargebacks.

This module:
  1. Detects whether an incoming PO text contains a matrix format.
  2. Expands the matrix into per-SKU line items for A2000 order entry.
  3. Cross-references buyer item codes (Walgreens internal IDs) to vendor SKUs.
  4. Validates every expanded SKU has a GTIN for GS1-128 label generation.

Reference: docs/WHOLESALE_RESEARCH.md — Section 6 (Apparel-Specific Complexity),
           lifecycle Stage 6 (Size/Color Matrix Parsing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from adapters.po_parser import LineItem


@dataclass
class ItemCrossReference:
    """Mapping between a buyer's internal item code and the vendor's A2000 SKU.

    Walgreens assigns its own item codes that do not match the vendor's style
    numbers. Without this cross-reference, every matrix expansion produces
    SKUs that A2000 cannot match to the item master.

    Attributes
    ----------
    buyer_item_code:
        Walgreens' internal item identifier as it appears on the 850 PO.
    vendor_sku:
        Vendor's A2000 item code / style number.
    gtin:
        14-digit GTIN required for GS1-128 label generation. If None, this
        SKU cannot be shipped to Walgreens without a UPC being assigned first.
    season_code:
        Optional season code in A2000 format (e.g. "SP26", "FA26"). Used to
        validate the PO is entered against an open season.
    """

    buyer_item_code: str
    vendor_sku: str
    gtin: Optional[str] = None
    season_code: Optional[str] = None
    color_code: Optional[str] = None
    size_code: Optional[str] = None


def detect_matrix_format(po_text: str) -> bool:
    """Return True if the PO text appears to contain a size-color matrix.

    Heuristics checked:
      - Presence of common size tokens (XS/S/M/L/XL/XXL or numeric sizes 2–20)
        appearing as column headers within a tabular block.
      - Multiple rows referencing the same style number with different color codes.
      - Headers matching known apparel patterns ("QTY BY SIZE", "SIZE BREAK", etc.)

    Parameters
    ----------
    po_text:
        Raw extracted text of the PO document (from PDF, Excel, or EDI 850).

    Returns
    -------
    bool
        True if matrix format is detected; False if the PO appears to be flat
        line items or a non-apparel format.

    Raises
    ------
    NotImplementedError
        Until Phase 5b implementation is complete.
    """
    raise NotImplementedError("Phase 5b — see docs/BUILD_PLAN.md")


def expand_matrix(
    matrix: dict,
    item_xref: dict[str, ItemCrossReference],
) -> list[LineItem]:
    """Expand a parsed size-color matrix into flat per-SKU line items.

    Parameters
    ----------
    matrix:
        Parsed matrix structure. Shape::

            {
                "style": "BT-2210",
                "buyer_item_code": "WAG-123456",
                "colors": {
                    "NVY": {
                        "XS": 50, "S": 100, "M": 150,
                        "L": 120, "XL": 80, "XXL": 50,
                    },
                    "RED": {
                        "XS": 30, "S": 60, "M": 90, ...
                    }
                },
                "unit_price": 12.50,
            }

    item_xref:
        Mapping from buyer item codes to :class:`ItemCrossReference` records.
        Key is ``buyer_item_code``.

    Returns
    -------
    list[LineItem]
        One :class:`~adapters.po_parser.LineItem` per size-color combination
        with a non-zero quantity. The ``sku`` field is set to the vendor's
        A2000 item code + size + color composite key, and ``upc`` is populated
        from the GTIN in the cross-reference record.

    Raises
    ------
    KeyError
        If a buyer item code in the matrix is not found in ``item_xref``.
    ValueError
        If any expanded SKU has no GTIN — caller should escalate before entry.
    NotImplementedError
        Until Phase 5b implementation is complete.
    """
    raise NotImplementedError("Phase 5b — see docs/BUILD_PLAN.md")
