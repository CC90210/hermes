"""GS1-128 / UCC-128 carton label generator.

Implements Phase 2b — ASN + Carton Labels (PRE-LAUNCH FOR WALGREENS).

Every carton shipped to Walgreens must carry a GS1-128 label encoding a unique
SSCC-18 (Serial Shipping Container Code). The SSCC data on the physical label
must be byte-for-byte identical to the SSCC transmitted in the EDI 856 ASN —
any mismatch generates an automatic chargeback under the Cost Recovery Program.

Label spec (Walgreens):
  - Size:        4" × 6" thermal label
  - Symbology:   GS1-128 (Code 128), minimum 203 DPI (300 DPI recommended)
  - Barcode ht:  minimum 1 inch
  - Quiet zones: 0.25" on each side
  - Required AI: (00) SSCC-18, (400) PO Number, (410) Ship-To DC GLN
  - Primary output: ZPL string for Zebra thermal printers
  - Fallback output: PDF (reportlab) for non-Zebra environments

Reference: docs/WHOLESALE_RESEARCH.md — Section 2 (GS1-128 / UCC-128 Carton
           Label Requirements), lifecycle Stage 12 (Carrier Label and BOL).
GS1 US SSCC specification: https://www.gs1us.org/upcs-barcodes-prefixes/sscc
Walgreens label template: https://docs.orderful.com/changelog/walgreens-ucc-128-label-support
"""

from __future__ import annotations


def generate_label_zpl(
    sscc: str,
    gtin: str,
    po_number: str,
    ship_to: dict,
    qty: int,
) -> str:
    """Generate a Zebra ZPL II string for a GS1-128 compliant carton label.

    The returned string is sent directly to a Zebra thermal printer via raw
    TCP/IP socket (port 9100) or USB. No intermediate rendering is required.

    Parameters
    ----------
    sscc:
        18-digit SSCC as computed by :func:`compute_sscc`. Do NOT include the
        Application Identifier (00) here — it is injected by the ZPL template.
    gtin:
        14-digit GTIN of the item packed in this carton (UPC-12 zero-padded to 14).
    po_number:
        Walgreens purchase order number (Application Identifier 400 field).
    ship_to:
        Dictionary with keys:
        - ``"name"``    — DC or store name
        - ``"address"`` — street address
        - ``"city"``    — city
        - ``"state"``   — 2-letter state code
        - ``"zip"``     — ZIP code
        - ``"gln"``     — 13-digit GLN of the destination DC (AI 410)
    qty:
        Number of eaches packed in this carton (human-readable on label).

    Returns
    -------
    str
        ZPL II string ready to send to a Zebra printer. Encoding is UTF-8.

    Raises
    ------
    ValueError
        If ``sscc`` is not 18 digits or fails Modulo-10 check digit validation.
    NotImplementedError
        Until Phase 2b implementation is complete.
    """
    raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")


def generate_label_pdf(
    sscc: str,
    gtin: str,
    po_number: str,
    ship_to: dict,
    qty: int,
) -> bytes:
    """Generate a PDF carton label for environments without a Zebra thermal printer.

    Produces a 4" × 6" PDF (288pt × 432pt) with a GS1-128 barcode rendered via
    python-barcode or barcode128, matching Walgreens minimum resolution and quiet
    zone requirements.

    Parameters are identical to :func:`generate_label_zpl`.

    Returns
    -------
    bytes
        PDF bytes suitable for printing or saving to disk.

    Raises
    ------
    ValueError
        If ``sscc`` fails check digit validation.
    NotImplementedError
        Until Phase 2b implementation is complete.
    """
    raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")


def compute_sscc(
    extension_digit: int,
    gs1_company_prefix: str,
    serial_ref: int,
) -> str:
    """Compute a valid 18-digit SSCC with Modulo-10 check digit.

    SSCC structure (18 digits total):
        [1 extension digit] + [GS1 Company Prefix, 7–10 digits] +
        [serial reference, padded] + [1 Modulo-10 check digit]

    The extension digit is typically 0 for standard cartons. The GS1 Company
    Prefix is assigned by GS1 US to the brand owner.

    Parameters
    ----------
    extension_digit:
        Single digit (0–9). Commonly 0 for outbound cartons.
    gs1_company_prefix:
        The brand owner's GS1 Company Prefix (7–10 digits, no leading zeros stripped).
    serial_ref:
        Sequential serial reference number for this carton. The function pads this
        to fill the remaining SSCC digits before the check digit.

    Returns
    -------
    str
        18-digit SSCC string (digits only, no spaces or Application Identifiers).

    Raises
    ------
    ValueError
        If the resulting pre-check string is not 17 digits, or if ``extension_digit``
        is not 0–9.
    NotImplementedError
        Until Phase 2b implementation is complete.

    Examples
    --------
    >>> compute_sscc(0, "0614141", 12345)
    "006141410000123453"
    """
    raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")
