"""
tests/test_a2000_mock.py
------------------------
Tests for adapters/a2000_client.py MockA2000Client and the factory.

No external services required — MockA2000Client is entirely in-process.
"""

from __future__ import annotations

import pytest

from adapters.a2000_client import MockA2000Client, get_a2000_client
from adapters.po_parser import LineItem, POData


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_client() -> MockA2000Client:
    return MockA2000Client()


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
        line_items=[
            LineItem(sku="LWG-1001", description="Premium Cotton T-Shirt - Black M", quantity=144, unit_price=4.25),
            LineItem(sku="LWG-2050", description="Athletic Sock 6-Pack White", quantity=72, unit_price=8.50),
        ],
    )


# ---------------------------------------------------------------------------
# test_mock_create_order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_create_order(mock_client: MockA2000Client, sample_po: POData) -> None:
    """create_order returns a successful OrderResult with a non-empty order_id."""
    result = await mock_client.create_order(sample_po)

    assert result.success is True
    assert result.order_id.startswith("MOCK-")
    assert result.invoice_number is not None
    assert result.invoice_number.startswith("INV-")
    assert "mock order created" in result.message.lower()


@pytest.mark.asyncio
async def test_mock_create_order_stores_internally(
    mock_client: MockA2000Client, sample_po: POData
) -> None:
    """Created order can be retrieved with get_order."""
    result = await mock_client.create_order(sample_po)
    order = await mock_client.get_order(result.order_id)

    assert order["order_id"] == result.order_id
    assert order["po_number"] == "PO-2026-04567"
    assert order["customer_name"] == "Walgreens #04231"
    assert order["line_item_count"] == 2


# ---------------------------------------------------------------------------
# test_mock_get_invoice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_get_invoice(mock_client: MockA2000Client, sample_po: POData) -> None:
    """get_invoice returns bytes containing mock PDF content."""
    result = await mock_client.create_order(sample_po)
    pdf_bytes = await mock_client.get_invoice(result.order_id)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # The mock returns a text stub that starts with %PDF
    assert pdf_bytes.startswith(b"%PDF")
    # Invoice and order IDs appear in the body
    decoded = pdf_bytes.decode()
    assert result.order_id in decoded
    assert result.invoice_number in decoded


@pytest.mark.asyncio
async def test_mock_get_invoice_unknown_order_raises(mock_client: MockA2000Client) -> None:
    """get_invoice raises KeyError for an order that was never created."""
    with pytest.raises(KeyError):
        await mock_client.get_invoice("MOCK-DOESNOTEXIST")


# ---------------------------------------------------------------------------
# test_mock_print_order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_print_order(mock_client: MockA2000Client, sample_po: POData) -> None:
    """print_order returns True for an existing order."""
    result = await mock_client.create_order(sample_po)
    printed = await mock_client.print_order(result.order_id)

    assert printed is True


@pytest.mark.asyncio
async def test_mock_print_order_unknown_raises(mock_client: MockA2000Client) -> None:
    """print_order on an unknown order still raises because get_order is called internally."""
    # The mock delegates to get_order, which raises KeyError for unknown IDs
    with pytest.raises(KeyError):
        await mock_client.print_order("MOCK-UNKNOWN")


# ---------------------------------------------------------------------------
# test_factory_returns_mock_for_mock_mode
# ---------------------------------------------------------------------------

def test_factory_returns_mock_for_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_a2000_client('mock') returns a MockA2000Client instance."""
    client = get_a2000_client("mock")
    assert isinstance(client, MockA2000Client)


def test_factory_uses_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_a2000_client() without args reads A2000_MODE from env."""
    monkeypatch.setenv("A2000_MODE", "mock")
    client = get_a2000_client()
    assert isinstance(client, MockA2000Client)


def test_factory_raises_for_unknown_mode() -> None:
    """get_a2000_client raises ValueError for an unrecognised mode string."""
    with pytest.raises(ValueError, match="Unknown A2000_MODE"):
        get_a2000_client("telepathy")


# ---------------------------------------------------------------------------
# Multiple independent orders
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_multiple_orders_are_independent(sample_po: POData) -> None:
    """Each create_order call generates a unique order_id and invoice_number."""
    client = MockA2000Client()
    r1 = await client.create_order(sample_po)
    r2 = await client.create_order(sample_po)

    assert r1.order_id != r2.order_id
    assert r1.invoice_number != r2.invoice_number
