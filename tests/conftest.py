"""
tests/conftest.py
-----------------
Shared pytest fixtures for Hermes.

All fixtures that touch env vars use monkeypatch so they are automatically
undone after each test — no global state leaks.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from adapters.po_parser import LineItem, POData


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set every required env var to safe test values."""
    env_vars = {
        "EMAIL_USER": "test@example.com",
        "EMAIL_PASSWORD": "test-password",
        "EMAIL_HOST": "imap.example.com",
        "EMAIL_IMAP_PORT": "993",
        "EMAIL_SMTP_HOST": "smtp.example.com",
        "EMAIL_SMTP_PORT": "587",
        "OLLAMA_HOST": "http://localhost:11434",
        "OLLAMA_MODEL": "qwen2.5:32b",
        "A2000_MODE": "mock",
        "A2000_API_URL": "http://a2000.example.com",
        "A2000_API_KEY": "test-api-key",
        "ESCALATION_EMAIL": "escalate@example.com",
        "LOG_LEVEL": "WARNING",
        "COMPANY_NAME": "Test Distribution Co.",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_db_path(tmp_path: Path) -> Path:
    """An isolated SQLite file that is deleted after each test."""
    return tmp_path / "test.db"


# ---------------------------------------------------------------------------
# PO text / data
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_po_text() -> str:
    """Multi-line plain-text PO matching tests/fixtures/sample_po.txt."""
    return (FIXTURES_DIR / "sample_po.txt").read_text(encoding="utf-8")


@pytest.fixture()
def sample_po_data() -> POData:
    """A fully populated POData instance — no Ollama call required."""
    return POData(
        po_number="PO-2026-04567",
        customer_name="Walgreens #04231",
        customer_email="purchasing@walgreens.com",
        customer_address="1234 Market Street, Chicago, IL 60601",
        ship_to_address="5500 Industrial Blvd, Aurora, IL 60504",
        order_date="2026-04-15",
        ship_date="2026-04-22",
        notes="Please ship via standard freight. Confirm receipt by EOD 2026-04-16.",
        line_items=[
            LineItem(
                sku="LWG-1001",
                description="Premium Cotton T-Shirt - Black M",
                quantity=144,
                unit_price=4.25,
            ),
            LineItem(
                sku="LWG-1002",
                description="Premium Cotton T-Shirt - Black L",
                quantity=144,
                unit_price=4.25,
            ),
            LineItem(
                sku="LWG-2050",
                description="Athletic Sock 6-Pack White",
                quantity=72,
                unit_price=8.50,
            ),
        ],
        raw_text=(FIXTURES_DIR / "sample_po.txt").read_text(encoding="utf-8"),
        internal_order_id=None,
    )
