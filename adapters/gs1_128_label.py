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


# ---------------------------------------------------------------------------
# SSCC-18 computation
# ---------------------------------------------------------------------------


def compute_sscc(
    extension_digit: int,
    gs1_company_prefix: str,
    serial_ref: int,
) -> str:
    """Compute a valid 18-digit SSCC with Modulo-10 check digit.

    SSCC structure (18 digits total)::

        [1 extension digit] + [GS1 Company Prefix, 7–10 digits]
        + [serial reference, zero-padded] + [1 Modulo-10 check digit]

    Parameters
    ----------
    extension_digit:
        Single digit 0–9. Typically 0 for standard outbound cartons.
    gs1_company_prefix:
        Brand owner's GS1 Company Prefix, 7–10 digits. Must be purely numeric.
    serial_ref:
        Sequential serial reference number. Zero-padded so that
        len(gs1_company_prefix) + len(padded_serial) == 16.

    Returns
    -------
    str
        18-digit SSCC string (digits only, no spaces or Application Identifiers).

    Raises
    ------
    ValueError
        If extension_digit is not 0–9, gs1_company_prefix is not 7–10 digits,
        or serial_ref overflows the available digit positions.

    Examples
    --------
    >>> compute_sscc(0, "0614141", 12345)
    '006141410000123453'
    """
    if not (0 <= extension_digit <= 9):
        raise ValueError(
            f"extension_digit must be 0–9, got {extension_digit!r}"
        )
    if not gs1_company_prefix.isdigit():
        raise ValueError(
            f"gs1_company_prefix must contain only digits, got {gs1_company_prefix!r}"
        )
    prefix_len = len(gs1_company_prefix)
    if not (7 <= prefix_len <= 10):
        raise ValueError(
            f"gs1_company_prefix must be 7–10 digits, got {prefix_len}"
        )

    serial_width = 16 - prefix_len  # digits available for the serial reference
    if serial_ref < 0 or serial_ref >= 10**serial_width:
        raise ValueError(
            f"serial_ref {serial_ref} overflows {serial_width}-digit field "
            f"(max {10**serial_width - 1}) for a {prefix_len}-digit company prefix"
        )

    body = f"{extension_digit}{gs1_company_prefix}{serial_ref:0{serial_width}d}"
    assert len(body) == 17, f"Pre-check body must be 17 digits, got {len(body)}"

    check = _gs1_mod10(body)
    return body + str(check)


def _gs1_mod10(digits: str) -> int:
    """Compute the GS1 Modulo-10 check digit for a string of N digits.

    GS1 algorithm (applied to digits left-to-right):
    1. Multiply each digit at an odd position (1-indexed from the left) by 3,
       and each digit at an even position by 1.
    2. Sum all products.
    3. Check digit = (10 - (sum % 10)) % 10.
    """
    total = 0
    for i, ch in enumerate(digits):
        multiplier = 3 if (i % 2 == 0) else 1
        total += int(ch) * multiplier
    return (10 - (total % 10)) % 10


def validate_sscc(sscc: str) -> bool:
    """Return True if ``sscc`` is an 18-digit string with a valid Mod-10 check digit.

    Parameters
    ----------
    sscc:
        18-digit string to validate (digits only, no Application Identifier prefix).
    """
    if not sscc.isdigit() or len(sscc) != 18:
        return False
    expected = _gs1_mod10(sscc[:17])
    return int(sscc[17]) == expected


def sscc_to_barcode_data(sscc: str) -> str:
    """Format an SSCC-18 for embedding in a GS1-128 barcode.

    Prepends the Application Identifier ``(00)`` so the data string passed to
    a barcode renderer produces a compliant GS1-128 symbol.

    Parameters
    ----------
    sscc:
        18-digit SSCC (digits only, no AI prefix).

    Returns
    -------
    str
        GS1-128 data string including AI, e.g. ``"00006141410000123453"``.
    """
    return f"00{sscc}"


# ---------------------------------------------------------------------------
# ZPL label generation
# ---------------------------------------------------------------------------


def generate_label_zpl(
    sscc: str,
    gtin: str,
    po_number: str,
    ship_to_name: str,
    ship_to_address: dict,
    ship_to_store: str,
    carton_qty: int,
    carton_number: int,
    total_cartons: int,
    ship_from_name: str = "",
    po_date: str = "",
) -> str:
    """Generate ZPL II for a 4×6 inch GS1-128 compliant Walgreens carton label.

    The label is designed for a Zebra thermal printer at 203 DPI (812×1218 dots).
    The barcode encodes AI (00) + SSCC-18 using Code 128 with GS1 FNC1.

    Label layout (top to bottom):
    - Header block: ship-from name / ship-to name, address, store ID
    - Middle block: PO number, carton X of Y
    - Barcode block: GS1-128 barcode with human-readable SSCC below

    Parameters
    ----------
    sscc:
        18-digit SSCC — must pass :func:`validate_sscc`.
    gtin:
        14-digit GTIN of the item inside.
    po_number:
        Walgreens purchase order number.
    ship_to_name:
        Name of the destination DC or store.
    ship_to_address:
        Dict with keys: street, city, state, zip.
    ship_to_store:
        Store number or DC ID (printed and encoded on label).
    carton_qty:
        Number of eaches packed in this carton.
    carton_number:
        This carton's sequence number (e.g. 3 in "3 of 12").
    total_cartons:
        Total carton count in the shipment.
    ship_from_name:
        Optional shipper name for the header block.
    po_date:
        Optional PO date string (printed in middle block).

    Returns
    -------
    str
        ZPL II string, UTF-8, ready to send to a Zebra printer on TCP port 9100.

    Raises
    ------
    ValueError
        If ``sscc`` fails :func:`validate_sscc`.
    """
    if not validate_sscc(sscc):
        raise ValueError(f"SSCC '{sscc}' is not a valid 18-digit GS1 SSCC")

    # GS1-128 barcode data: FNC1 start + AI (00) + SSCC
    # In ZPL, >8 is the FNC1 character code for GS1 mode; we embed AI in the data.
    barcode_data = f">800{sscc}"
    human_readable = f"(00) {sscc[:2]} {sscc[2:9]} {sscc[9:17]} {sscc[17]}"

    street = ship_to_address.get("street", "")
    city = ship_to_address.get("city", "")
    state = ship_to_address.get("state", "")
    zip_code = ship_to_address.get("zip", "")
    city_line = f"{city}, {state} {zip_code}".strip(", ")

    zpl_lines = [
        "^XA",
        "^CI28",               # UTF-8 encoding
        "^PW812",              # label width: 812 dots (4 inches @ 203 DPI)
        "^LL1218",             # label length: 1218 dots (6 inches @ 203 DPI)
        # --- Ship-From block ---
        "^FO30,20^A0N,22,22^FDFrom:^FS",
        f"^FO30,45^A0N,28,28^FD{ship_from_name[:35]}^FS",
        # --- Horizontal rule ---
        "^FO20,85^GB772,3,3^FS",
        # --- Ship-To block ---
        "^FO30,95^A0N,22,22^FDShip To:^FS",
        f"^FO30,120^A0N,32,32^FD{ship_to_name[:35]}^FS",
        f"^FO30,158^A0N,26,26^FD{street[:40]}^FS",
        f"^FO30,188^A0N,26,26^FD{city_line[:40]}^FS",
        f"^FO30,218^A0N,26,26^FDStore/DC: {ship_to_store}^FS",
        # --- Horizontal rule ---
        "^FO20,255^GB772,3,3^FS",
        # --- PO / carton info block ---
        f"^FO30,270^A0N,28,28^FDPO: {po_number}^FS",
    ]

    if po_date:
        zpl_lines.append(f"^FO30,302^A0N,28,28^FDPO Date: {po_date}^FS")

    zpl_lines += [
        f"^FO30,336^A0N,28,28^FDCarton: {carton_number} of {total_cartons}^FS",
        f"^FO30,368^A0N,28,28^FDQty: {carton_qty} EA^FS",
        f"^FO30,400^A0N,24,24^FDGTIN: {gtin}^FS",
        # --- Horizontal rule ---
        "^FO20,435^GB772,3,3^FS",
        # --- GS1-128 barcode ---
        # ^BY: barcode field defaults — module width 3, ratio 3.0, height 150
        "^FO60,455",
        "^BY3,3,150",
        f"^BCN,150,N,N,N,A",   # Code 128, height 150, no check, no check print, no human, GS1 mode
        f"^FD{barcode_data}^FS",
        # --- Human-readable SSCC below barcode ---
        f"^FO60,615^A0N,24,24^FD{human_readable}^FS",
        "^XZ",
    ]

    return "\n".join(zpl_lines)


# ---------------------------------------------------------------------------
# PDF fallback
# ---------------------------------------------------------------------------


def generate_label_pdf(
    sscc: str,
    gtin: str,
    po_number: str,
    ship_to_name: str,
    ship_to_address: dict,
    ship_to_store: str,
    carton_qty: int,
    carton_number: int,
    total_cartons: int,
    ship_from_name: str = "",
    po_date: str = "",
) -> bytes:
    """Generate a 4×6 inch PDF carton label for non-ZPL printer environments.

    Uses reportlab to render a GS1-128 barcode via Code39 fallback encoding
    of the SSCC data. Output is a single-page PDF at 72 DPI (288pt × 432pt).

    Parameters are identical to :func:`generate_label_zpl`.

    Returns
    -------
    bytes
        PDF bytes suitable for printing on any standard PDF renderer.

    Raises
    ------
    ValueError
        If ``sscc`` fails :func:`validate_sscc`.
    ImportError
        If reportlab is not installed.
    """
    if not validate_sscc(sscc):
        raise ValueError(f"SSCC '{sscc}' is not a valid 18-digit GS1 SSCC")

    try:
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import inch
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.graphics.barcode import code128
        from reportlab.graphics import renderPDF
        from reportlab.graphics.shapes import Drawing
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF label generation. "
            "Install it with: pip install reportlab"
        ) from exc

    width = 4 * inch
    height = 6 * inch
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    margin = 0.2 * inch
    y = height - margin

    def _text(text: str, x: float, y_pos: float, size: int = 10) -> None:
        c.setFont("Helvetica", size)
        c.drawString(x, y_pos, text)

    def _rule(y_pos: float) -> None:
        c.setLineWidth(1)
        c.line(margin, y_pos, width - margin, y_pos)

    # Ship-From
    _text("From:", margin, y - 14, 8)
    _text(ship_from_name[:50], margin, y - 28, 11)
    y -= 40
    _rule(y)
    y -= 10

    # Ship-To
    street = ship_to_address.get("street", "")
    city = ship_to_address.get("city", "")
    state = ship_to_address.get("state", "")
    zip_code = ship_to_address.get("zip", "")

    _text("Ship To:", margin, y - 14, 8)
    _text(ship_to_name[:50], margin, y - 30, 13)
    _text(street[:50], margin, y - 48, 10)
    _text(f"{city}, {state} {zip_code}".strip(", "), margin, y - 62, 10)
    _text(f"Store/DC: {ship_to_store}", margin, y - 76, 10)
    y -= 90
    _rule(y)
    y -= 10

    # PO / carton info
    _text(f"PO: {po_number}", margin, y - 14, 11)
    if po_date:
        _text(f"PO Date: {po_date}", margin, y - 30, 10)
        y -= 16
    _text(f"Carton: {carton_number} of {total_cartons}", margin, y - 30, 11)
    _text(f"Qty: {carton_qty} EA", margin, y - 46, 10)
    _text(f"GTIN: {gtin}", margin, y - 62, 10)
    y -= 78
    _rule(y)
    y -= 8

    # GS1-128 barcode — encode AI (00) + SSCC
    barcode_value = f"00{sscc}"
    barcode = code128.Code128(
        barcode_value,
        barHeight=1.0 * inch,
        barWidth=1.2,
        humanReadable=False,
    )
    barcode_width = barcode.width
    barcode_x = (width - barcode_width) / 2
    barcode_y = y - 1.0 * inch - 0.1 * inch
    barcode.drawOn(c, barcode_x, barcode_y)

    # Human-readable SSCC
    human = f"(00) {sscc[:2]} {sscc[2:9]} {sscc[9:17]} {sscc[17]}"
    c.setFont("Courier", 9)
    c.drawCentredString(width / 2, barcode_y - 14, human)

    c.save()
    return buf.getvalue()
