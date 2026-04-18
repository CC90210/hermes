from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from adapters.a2000_client import A2000ClientBase

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

COMPANY_NAME: str = os.environ.get("COMPANY_NAME", "Lowinger Distribution")  # client business name — do not rename

_BODY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 14px; color: #222; }}
    .header {{ margin-bottom: 20px; }}
    .highlight {{ font-weight: bold; }}
    .footer {{ margin-top: 30px; color: #555; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="header">
    <p>Dear {customer_name},</p>
  </div>
  <p>
    Please find attached <span class="highlight">Invoice {invoice_number}</span>
    in respect of your Purchase Order <span class="highlight">{po_number}</span>.
  </p>
  <p>
    If you have any questions regarding this invoice, please do not hesitate
    to contact us.
  </p>
  <p>Thank you for your business.</p>
  <div class="footer">
    <p>
      Warm regards,<br />
      <strong>{company_name}</strong>
    </p>
  </div>
</body>
</html>
"""


@dataclass
class InvoicePackage:
    invoice_pdf: bytes
    invoice_number: str
    customer_email: str
    subject_line: str
    body_html: str


async def get_invoice_for_order(
    order_id: str,
    a2000_client: A2000ClientBase,
    *,
    customer_name: Optional[str] = None,
    customer_email: Optional[str] = None,
    po_number: Optional[str] = None,
    invoice_number: Optional[str] = None,
) -> InvoicePackage:
    """
    Retrieve the invoice PDF for a completed order and build an email package.

    Parameters
    ----------
    order_id:
        The internal order ID returned by A2000ClientBase.create_order.
    a2000_client:
        An instantiated A2000 client (any mode).
    customer_name:
        Display name used in the email greeting. Falls back to order metadata.
    customer_email:
        Recipient address. Falls back to order metadata.
    po_number:
        Buyer's PO reference for the subject line. Falls back to order metadata.
    invoice_number:
        Invoice number. Falls back to order metadata if available.
    """
    invoice_pdf = await a2000_client.get_invoice(order_id)

    order_meta: dict = {}  # type: ignore[type-arg]
    try:
        order_meta = await a2000_client.get_order(order_id)
    except (NotImplementedError, KeyError):
        pass

    resolved_invoice_number = (
        invoice_number
        or order_meta.get("invoice_number")
        or order_id
    )
    resolved_po_number = (
        po_number
        or order_meta.get("po_number")
        or "N/A"
    )
    resolved_customer_name = (
        customer_name
        or order_meta.get("customer_name")
        or "Valued Customer"
    )
    resolved_customer_email = (
        customer_email
        or order_meta.get("customer_email")
        or ""
    )

    subject_line = (
        f"Invoice {resolved_invoice_number} — PO {resolved_po_number} | {COMPANY_NAME}"
    )

    body_html = _BODY_TEMPLATE.format(
        customer_name=resolved_customer_name,
        invoice_number=resolved_invoice_number,
        po_number=resolved_po_number,
        company_name=COMPANY_NAME,
    )

    return InvoicePackage(
        invoice_pdf=invoice_pdf,
        invoice_number=resolved_invoice_number,
        customer_email=resolved_customer_email,
        subject_line=subject_line,
        body_html=body_html,
    )
