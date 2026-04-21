"""
tests/test_po_parser.py
-----------------------
Tests for adapters/po_parser.py.

Ollama HTTP calls are intercepted with respx so the suite runs fully offline.
PDF extraction uses a minimal stub instead of a real pdfplumber fixture to
avoid binary fixture files in the repo.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import respx
from httpx import Response

from adapters.po_parser import (
    LineItem,
    POData,
    _build_po_data,
    _extract_text_edi,
    parse_po,
    validate_po,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_EXTRACTED: dict = {
    "po_number": "PO-2026-04567",
    "customer_name": "Walgreens #04231",
    "customer_email": "purchasing@walgreens.com",
    "customer_address": "1234 Market Street, Chicago, IL 60601",
    "ship_to_address": "5500 Industrial Blvd, Aurora, IL 60504",
    "order_date": "2026-04-15",
    "ship_date": "2026-04-22",
    "notes": "Please ship via standard freight.",
    "line_items": [
        {"sku": "LWG-1001", "description": "Premium Cotton T-Shirt - Black M", "quantity": 144, "unit_price": 4.25, "upc": None},
        {"sku": "LWG-1002", "description": "Premium Cotton T-Shirt - Black L", "quantity": 144, "unit_price": 4.25, "upc": None},
        {"sku": "LWG-2050", "description": "Athletic Sock 6-Pack White", "quantity": 72, "unit_price": 8.50, "upc": None},
    ],
}


def _ollama_response(extracted: dict) -> Response:
    """Build the JSON shape that Ollama /api/generate returns."""
    return Response(200, json={"response": json.dumps(extracted)})


# ---------------------------------------------------------------------------
# test_parse_plain_text_po
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_parse_plain_text_po(sample_po_text: str) -> None:
    """parse_po on plain text routes to Ollama and returns populated POData."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=_ollama_response(_SAMPLE_EXTRACTED)
    )

    content = sample_po_text.encode()
    po = await parse_po(content, "po.txt", "text/plain")

    assert po.po_number == "PO-2026-04567"
    assert po.customer_name == "Walgreens #04231"
    assert po.customer_email == "purchasing@walgreens.com"
    assert po.ship_date == "2026-04-22"
    assert len(po.line_items) == 3

    skus = [item.sku for item in po.line_items]
    assert "LWG-1001" in skus
    assert "LWG-2050" in skus

    first = po.line_items[0]
    assert first.quantity == 144
    assert abs(first.unit_price - 4.25) < 1e-6


# ---------------------------------------------------------------------------
# test_parse_pdf_po
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_parse_pdf_po(sample_po_text: str) -> None:
    """parse_po with a .pdf filename triggers PDF path; pdfplumber is mocked."""
    respx.post("http://localhost:11434/api/generate").mock(
        return_value=_ollama_response(_SAMPLE_EXTRACTED)
    )

    # Stub pdfplumber so we don't need a real PDF binary
    mock_page = MagicMock()
    mock_page.extract_text.return_value = sample_po_text
    mock_pdf_ctx = MagicMock()
    mock_pdf_ctx.__enter__ = MagicMock(return_value=mock_pdf_ctx)
    mock_pdf_ctx.__exit__ = MagicMock(return_value=False)
    mock_pdf_ctx.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf_ctx):
        po = await parse_po(b"%PDF-1.4 fake", "walgreens_po.pdf", "application/pdf")

    assert po.po_number == "PO-2026-04567"
    assert len(po.line_items) == 3
    # Verify pdfplumber text was fed into the Ollama call
    assert po.raw_text == sample_po_text


# ---------------------------------------------------------------------------
# test_validate_po_missing_po_number
# ---------------------------------------------------------------------------

def test_validate_po_missing_po_number(sample_po_data: POData) -> None:
    """validate_po returns an error when po_number is absent."""
    import dataclasses
    po = dataclasses.replace(sample_po_data, po_number=None)
    errors = validate_po(po)
    assert any("PO number" in e for e in errors), f"Expected PO number error, got: {errors}"


def test_validate_po_blank_po_number(sample_po_data: POData) -> None:
    """validate_po treats a whitespace-only po_number as missing."""
    import dataclasses
    po = dataclasses.replace(sample_po_data, po_number="   ")
    errors = validate_po(po)
    assert any("PO number" in e for e in errors)


# ---------------------------------------------------------------------------
# test_validate_po_no_line_items
# ---------------------------------------------------------------------------

def test_validate_po_no_line_items(sample_po_data: POData) -> None:
    """validate_po returns an error when line_items list is empty."""
    import dataclasses
    po = dataclasses.replace(sample_po_data, line_items=[])
    errors = validate_po(po)
    assert any("line item" in e.lower() for e in errors), f"Expected line items error, got: {errors}"


def test_validate_po_zero_quantity(sample_po_data: POData) -> None:
    """validate_po flags a line item with quantity <= 0."""
    bad_item = LineItem(sku="X", description="Test", quantity=0, unit_price=1.0)
    import dataclasses
    po = dataclasses.replace(sample_po_data, line_items=[bad_item])
    errors = validate_po(po)
    assert any("quantity" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# test_extract_edi_850_basic
# ---------------------------------------------------------------------------

def test_extract_edi_850_basic() -> None:
    """_extract_text_edi parses BEG, N1, and PO1 segments from an X12 850."""
    # Minimal well-formed X12 850 with * as element separator and ~ as segment sep
    edi = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       "
        "*260415*1200*^*00501*000000001*0*P*>~"
        "GS*PO*SENDER*RECEIVER*20260415*1200*1*X*005010~"
        "ST*850*0001~"
        "BEG*00*SA*PO-2026-04567**20260415~"
        "N1*BT*Walgreens #04231*92*WG04231~"
        "N3*1234 Market Street~"
        "N4*Chicago, IL 60601~"
        "PO1*0001*144*EA*4.25*PE*BP*LWG-1001*PD*Premium Cotton T-Shirt - Black M~"
        "PO1*0002*72*EA*8.50*PE*BP*LWG-2050*PD*Athletic Sock 6-Pack White~"
        "CTT*2~"
        "SE*10*0001~"
        "GE*1*1~"
        "IEA*1*000000001~"
    )

    result = _extract_text_edi(edi.encode())

    assert "PO-2026-04567" in result, "BEG PO number not extracted"
    assert "Walgreens #04231" in result, "N1 buyer name not extracted"
    assert "LWG-1001" in result, "PO1 SKU not extracted"
    assert "LWG-2050" in result, "Second PO1 SKU not extracted"
    assert "144" in result
    assert "72" in result


# ---------------------------------------------------------------------------
# test_build_po_data — pure unit, no HTTP
# ---------------------------------------------------------------------------

def test_build_po_data_populates_all_fields() -> None:
    """_build_po_data correctly maps extracted dict to POData dataclass."""
    po = _build_po_data(_SAMPLE_EXTRACTED, raw_text="raw")

    assert po.po_number == "PO-2026-04567"
    assert po.customer_email == "purchasing@walgreens.com"
    assert po.order_date == "2026-04-15"
    assert po.ship_date == "2026-04-22"
    assert len(po.line_items) == 3
    assert po.line_items[2].sku == "LWG-2050"
    assert po.line_items[2].quantity == 72
    assert abs(po.line_items[2].unit_price - 8.50) < 1e-6
    assert po.raw_text == "raw"
    assert po.internal_order_id is None


def test_build_po_data_handles_missing_fields() -> None:
    """_build_po_data does not raise when optional fields are absent."""
    minimal = {
        "po_number": "TEST-001",
        "customer_name": "Acme Corp",
        "line_items": [],
    }
    po = _build_po_data(minimal, raw_text="")
    assert po.customer_email is None
    assert po.ship_date is None
    assert po.line_items == []
