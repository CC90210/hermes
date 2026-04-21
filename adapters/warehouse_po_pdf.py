"""
adapters/warehouse_po_pdf.py
-----------------------------
Generates a human-readable warehouse PO PDF from a POData object.

Output is a single-page PDF suitable for printing on a standard printer
and physically submitting to the warehouse. Uses reportlab.

Layout:
  - Header: company name, "WAREHOUSE COPY", timestamp
  - Customer + ship-to block
  - Line-items table: SKU | Description | Qty | Unit Price | Total
  - Totals row
  - Signature / acknowledgement block
"""
from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adapters.po_parser import POData


def generate_warehouse_po(po: "POData", order_id: str) -> bytes:
    """Render a single-page warehouse PO PDF and return the raw bytes.

    Parameters
    ----------
    po:
        Fully-populated POData instance from the parser.
    order_id:
        Internal Hermes order ID (integer as string) — printed in the header
        so warehouse staff can cross-reference the system record.

    Returns
    -------
    bytes
        PDF bytes ready to be written to disk or passed to printer_tool.

    Raises
    ------
    ImportError
        If reportlab is not installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
            HRFlowable,
        )
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for warehouse PO PDF generation. "
            "Install with: pip install reportlab"
        ) from exc

    from datetime import datetime, timezone

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]

    bold_style = ParagraphStyle(
        "Bold",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=10,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.grey,
    )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    story = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    story.append(Paragraph("WAREHOUSE COPY — PURCHASE ORDER", h1))
    story.append(Spacer(1, 0.05 * inch))

    header_data = [
        [
            Paragraph(f"<b>Internal Order ID:</b> {order_id}", normal),
            Paragraph(f"<b>PO Number:</b> {po.po_number or 'N/A'}", normal),
            Paragraph(f"<b>Printed:</b> {now_str}", normal),
        ]
    ]
    header_table = Table(header_data, colWidths=[2.2 * inch, 2.2 * inch, 2.6 * inch])
    header_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.1 * inch))

    # -----------------------------------------------------------------------
    # Customer / Ship-To block
    # -----------------------------------------------------------------------
    story.append(Paragraph("CUSTOMER & SHIPPING DETAILS", h2))
    addr_data = [
        [
            Paragraph("<b>Customer:</b>", label_style),
            Paragraph(po.customer_name or "—", normal),
            Paragraph("<b>Ship To:</b>", label_style),
            Paragraph(po.ship_to_address or "—", normal),
        ],
        [
            Paragraph("<b>Email:</b>", label_style),
            Paragraph(po.customer_email or "—", normal),
            Paragraph("<b>Order Date:</b>", label_style),
            Paragraph(po.order_date or "—", normal),
        ],
        [
            Paragraph("<b>Bill To:</b>", label_style),
            Paragraph(po.customer_address or "—", normal),
            Paragraph("<b>Ship Date:</b>", label_style),
            Paragraph(po.ship_date or "—", normal),
        ],
    ]
    addr_table = Table(
        addr_data,
        colWidths=[1.0 * inch, 2.5 * inch, 1.0 * inch, 2.5 * inch],
    )
    addr_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    story.append(addr_table)

    if po.notes:
        story.append(Spacer(1, 0.05 * inch))
        story.append(Paragraph(f"<b>Notes:</b> {po.notes}", normal))

    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.1 * inch))

    # -----------------------------------------------------------------------
    # Line-items table
    # -----------------------------------------------------------------------
    story.append(Paragraph("LINE ITEMS", h2))

    col_headers = ["SKU", "Description", "Qty", "Unit Price", "Line Total"]
    table_data = [col_headers]

    grand_total = 0.0
    for item in po.line_items:
        line_total = (item.quantity or 0) * (item.unit_price or 0.0)
        grand_total += line_total
        table_data.append([
            item.sku or "—",
            item.description or "—",
            str(item.quantity or 0),
            f"${item.unit_price:.2f}" if item.unit_price else "$0.00",
            f"${line_total:.2f}",
        ])

    # Grand total row
    table_data.append(["", "", "", "TOTAL:", f"${grand_total:.2f}"])

    col_widths = [1.1 * inch, 3.0 * inch, 0.6 * inch, 1.1 * inch, 1.2 * inch]
    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(
        TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Body rows
            ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -2), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f5f5")]),
            # Numeric columns right-aligned
            ("ALIGN", (2, 1), (4, -1), "RIGHT"),
            # Grid
            ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#cccccc")),
            ("LINEABOVE", (0, -1), (-1, -1), 1.0, colors.black),
            # Total row
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 10),
            ("ALIGN", (3, -1), (4, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(items_table)
    story.append(Spacer(1, 0.3 * inch))

    # -----------------------------------------------------------------------
    # Signature block
    # -----------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("WAREHOUSE ACKNOWLEDGEMENT", h2))
    story.append(Spacer(1, 0.1 * inch))

    sig_data = [
        [
            Paragraph("Received by (print):", label_style),
            Paragraph("_" * 35, normal),
            Paragraph("Date:", label_style),
            Paragraph("_" * 20, normal),
        ],
        [
            Paragraph("Signature:", label_style),
            Paragraph("_" * 35, normal),
            Paragraph("Time:", label_style),
            Paragraph("_" * 20, normal),
        ],
    ]
    sig_table = Table(
        sig_data,
        colWidths=[1.1 * inch, 2.4 * inch, 0.7 * inch, 2.8 * inch],
    )
    sig_table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(sig_table)

    story.append(Spacer(1, 0.15 * inch))
    story.append(
        Paragraph(
            f"<i>Generated by Hermes — {now_str} — Order ID {order_id}</i>",
            ParagraphStyle("footer", parent=normal, fontSize=7, textColor=colors.grey),
        )
    )

    doc.build(story)
    return buf.getvalue()
