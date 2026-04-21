"""
tests/test_warehouse_po_pdf.py
-------------------------------
Tests for adapters/warehouse_po_pdf.py

Verifies PDF generation from POData without needing a printer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.po_parser import LineItem, POData
from adapters.warehouse_po_pdf import generate_warehouse_po


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_po() -> POData:
    return POData(
        po_number="PO-2026-04567",
        customer_name="Walgreens #04231",
        customer_email="purchasing@walgreens.com",
        customer_address="1234 Market Street, Chicago, IL 60601",
        ship_to_address="5500 Industrial Blvd, Aurora, IL 60504",
        order_date="2026-04-15",
        ship_date="2026-04-22",
        notes="Ship via standard freight.",
        line_items=[
            LineItem(sku="LWG-1001", description="Premium T-Shirt Black M", quantity=144, unit_price=4.25),
            LineItem(sku="LWG-1002", description="Premium T-Shirt Black L", quantity=72, unit_price=4.25),
            LineItem(sku="LWG-2050", description="Athletic Sock 6-Pack White", quantity=36, unit_price=8.50),
        ],
        raw_text="",
        internal_order_id="42",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateWarehousePo:
    def test_returns_non_zero_bytes(self, sample_po: POData):
        """PDF is generated and has content."""
        pdf = generate_warehouse_po(sample_po, "42")
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    def test_pdf_starts_with_pdf_header(self, sample_po: POData):
        """All PDFs begin with the %PDF magic bytes."""
        pdf = generate_warehouse_po(sample_po, "42")
        assert pdf[:4] == b"%PDF"

    def test_pdf_contains_customer_name(self, sample_po: POData):
        """Customer name appears in the extracted PDF text."""
        import io
        import pdfplumber

        pdf = generate_warehouse_po(sample_po, "42")
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert "Walgreens" in text

    def test_pdf_contains_all_skus(self, sample_po: POData):
        """Every line-item SKU appears in the extracted PDF text."""
        import io
        import pdfplumber

        pdf = generate_warehouse_po(sample_po, "42")
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            text = "\n".join(page.extract_text() or "" for page in doc.pages)
        for item in sample_po.line_items:
            assert item.sku in text, f"SKU {item.sku} not found in PDF text"

    def test_pdf_contains_order_id(self, sample_po: POData):
        """Internal order ID is embedded in the PDF."""
        pdf = generate_warehouse_po(sample_po, "42")
        assert b"42" in pdf

    def test_works_with_minimal_po(self):
        """Generates without error even when optional fields are missing."""
        minimal_po = POData(
            po_number="PO-MIN-001",
            customer_name="Test Customer",
            customer_email="",
            customer_address=None,
            ship_to_address=None,
            order_date=None,
            ship_date=None,
            notes=None,
            line_items=[
                LineItem(sku="SKU-1", description="Item A", quantity=10, unit_price=5.00),
            ],
            raw_text="",
            internal_order_id=None,
        )
        pdf = generate_warehouse_po(minimal_po, "0")
        assert len(pdf) > 0
