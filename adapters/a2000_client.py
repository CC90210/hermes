from __future__ import annotations

import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from adapters.po_parser import POData
from runtime.env_loader import load_env

load_env()

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    order_id: str
    success: bool
    message: str
    invoice_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class A2000ClientBase(ABC):
    @abstractmethod
    async def create_order(self, po: POData) -> OrderResult:
        ...

    @abstractmethod
    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        ...

    @abstractmethod
    async def get_invoice(self, order_id: str) -> bytes:
        ...

    @abstractmethod
    async def print_order(self, order_id: str) -> bool:
        ...

    async def validate(self) -> None:
        """Raise on connection failure. No-op for implementations that do not require
        an active connection at startup."""

    async def is_reachable(self) -> bool:
        """Return True if the backend is reachable. Default implementation returns True."""
        return True


# ---------------------------------------------------------------------------
# Mock client
# ---------------------------------------------------------------------------

class MockA2000Client(A2000ClientBase):
    """
    Simulates A2000 order entry without any real system calls.
    Suitable for demos, local development, and CI.
    """

    def __init__(self) -> None:
        self._orders: dict[str, dict] = {}  # type: ignore[type-arg]

    async def create_order(self, po: POData) -> OrderResult:
        order_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
        self._orders[order_id] = {
            "order_id": order_id,
            "invoice_number": invoice_number,
            "po_number": po.po_number,
            "customer_name": po.customer_name,
            "line_item_count": len(po.line_items),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "MockA2000Client: created order %s (invoice %s) for PO %s",
            order_id,
            invoice_number,
            po.po_number,
        )
        return OrderResult(
            order_id=order_id,
            success=True,
            message="Mock order created successfully.",
            invoice_number=invoice_number,
        )

    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        if order_id not in self._orders:
            raise KeyError(f"Order {order_id!r} not found in mock store.")
        return self._orders[order_id]

    async def get_invoice(self, order_id: str) -> bytes:
        order = await self.get_order(order_id)
        stub = (
            f"%PDF-1.4 mock invoice\n"
            f"Order: {order['order_id']}\n"
            f"Invoice: {order['invoice_number']}\n"
            f"PO: {order['po_number']}\n"
        )
        logger.info("MockA2000Client: returning stub invoice PDF for order %s", order_id)
        return stub.encode()

    async def print_order(self, order_id: str) -> bool:
        # Validate the order exists — raises KeyError for unknown IDs
        await self.get_order(order_id)
        logger.info("MockA2000Client: simulated print for order %s", order_id)
        return True


# ---------------------------------------------------------------------------
# API client (vendor-gated — stubs only)
# ---------------------------------------------------------------------------

class APIA2000Client(A2000ClientBase):
    """
    REST API integration with the A2000 POS system.

    The A2000 vendor API spec is not publicly available. Method signatures
    and field names are correct per the integration brief; raise
    NotImplementedError until the vendor provides API credentials and docs.
    """

    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self._api_url: str = api_url or os.environ.get("A2000_API_URL", "")
        self._api_key: str = api_key or os.environ.get("A2000_API_KEY", "")
        if not self._api_url or not self._api_key:
            raise EnvironmentError(
                "APIA2000Client requires A2000_API_URL and A2000_API_KEY"
            )
        self._http = httpx.AsyncClient(
            base_url=self._api_url,
            headers={"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"},
            timeout=30.0,
        )

    async def create_order(self, po: POData) -> OrderResult:
        raise NotImplementedError(
            "A2000 REST API not yet provisioned. Set A2000_MODE=mock or A2000_MODE=edi."
        )

    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        raise NotImplementedError("A2000 REST API not yet provisioned.")

    async def get_invoice(self, order_id: str) -> bytes:
        raise NotImplementedError("A2000 REST API not yet provisioned.")

    async def print_order(self, order_id: str) -> bool:
        raise NotImplementedError("A2000 REST API not yet provisioned.")

    async def aclose(self) -> None:
        await self._http.aclose()


# ---------------------------------------------------------------------------
# EDI client — writes X12 850 files for AS2/VAN pickup
# ---------------------------------------------------------------------------

class EDIA2000Client(A2000ClientBase):
    """
    Generates X12 850 EDI documents from POData and writes them to the
    configured output directory for AS2 or VAN transmission to A2000.
    """

    def __init__(self) -> None:
        self._output_dir = Path(
            os.environ.get("EDI_OUTPUT_DIR", "./storage/edi_out")
        )
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._sender_id: str = os.environ.get("EDI_SENDER_ID", "LOWINGER")
        self._receiver_id: str = os.environ.get("EDI_RECEIVER_ID", "A2000")

    def _build_x12_850(self, po: POData, order_id: str) -> str:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%y%m%d")
        time_str = now.strftime("%H%M")
        isa_control = f"{uuid.uuid4().int % 10**9:09d}"
        gs_control = now.strftime("%m%d%H%M%S")[:9]
        st_control = "0001"

        po_date = (po.order_date or now.strftime("%Y-%m-%d")).replace("-", "")
        ship_date = (po.ship_date or "").replace("-", "")

        segments: list[str] = []

        # ISA envelope
        segments.append(
            f"ISA*00*          *00*          *ZZ*{self._sender_id:<15}*ZZ*{self._receiver_id:<15}"
            f"*{date_str}*{time_str}*^*00501*{isa_control}*0*P*>"
        )
        segments.append(f"GS*PO*{self._sender_id}*{self._receiver_id}*{date_str}*{time_str}*{gs_control}*X*005010")
        segments.append(f"ST*850*{st_control}")

        # BEG — beginning segment
        segments.append(f"BEG*00*SA*{po.po_number or order_id}**{po_date}")

        # REF — ship date if present
        if ship_date:
            segments.append(f"DTM*002*{ship_date}")

        # N1 — Bill-to
        if po.customer_name:
            segments.append(f"N1*BT*{po.customer_name}*92*{po.customer_name[:20]}")
        if po.customer_address:
            parts = po.customer_address.split(",", 1)
            segments.append(f"N3*{parts[0].strip()}")
            if len(parts) > 1:
                segments.append(f"N4*{parts[1].strip()}")

        # N1 — Ship-to
        if po.ship_to_address and po.ship_to_address != po.customer_address:
            segments.append(f"N1*ST*{po.customer_name or 'SHIP TO'}*92*SHIPTO")
            parts = po.ship_to_address.split(",", 1)
            segments.append(f"N3*{parts[0].strip()}")
            if len(parts) > 1:
                segments.append(f"N4*{parts[1].strip()}")

        # PO1 — line items
        for idx, item in enumerate(po.line_items, start=1):
            po1_parts = [
                f"PO1*{idx:04d}",
                str(item.quantity),
                "EA",
                f"{item.unit_price:.2f}",
                "PE",
            ]
            if item.upc:
                po1_parts += ["UI", item.upc]
            if item.sku:
                po1_parts += ["BP", item.sku]
            if item.description:
                po1_parts += ["PD", item.description[:30]]
            segments.append("*".join(po1_parts))

        # CTT — transaction totals
        segments.append(f"CTT*{len(po.line_items)}")

        # SE — transaction set trailer
        segment_count = len(segments) - 2  # exclude ISA and GS
        segments.append(f"SE*{segment_count}*{st_control}")
        segments.append(f"GE*1*{gs_control}")
        segments.append(f"IEA*1*{isa_control}")

        return "~\n".join(segments) + "~\n"

    async def create_order(self, po: POData) -> OrderResult:
        order_id = f"EDI-{uuid.uuid4().hex[:8].upper()}"
        edi_content = self._build_x12_850(po, order_id)
        filename = f"{order_id}_{po.po_number or 'UNKNOWN'}.edi"
        out_path = self._output_dir / filename
        out_path.write_text(edi_content, encoding="ascii")
        logger.info("EDIA2000Client: wrote EDI 850 to %s", out_path)
        return OrderResult(
            order_id=order_id,
            success=True,
            message=f"EDI 850 written to {out_path}.",
            invoice_number=None,
        )

    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        # EDI is fire-and-forget; no inbound query possible without VAN/AS2 acknowledgement
        raise NotImplementedError(
            "EDI mode does not support order lookup. Check your VAN/AS2 acknowledgement queue."
        )

    async def get_invoice(self, order_id: str) -> bytes:
        raise NotImplementedError(
            "EDI mode does not support invoice retrieval. Invoices arrive as inbound 810 documents."
        )

    async def print_order(self, order_id: str) -> bool:
        raise NotImplementedError("EDI mode does not support remote print.")


# ---------------------------------------------------------------------------
# Playwright client (screen automation fallback — structure only)
# ---------------------------------------------------------------------------

class PlaywrightA2000Client(A2000ClientBase):
    """
    Screen automation fallback using Playwright.
    Navigates the A2000 web or desktop interface to enter orders manually.

    Implementation is environment-specific and requires:
    - A2000_BROWSER_URL: web URL or Electron app path
    - A2000_BROWSER_USER / A2000_BROWSER_PASS: login credentials
    """

    def __init__(self) -> None:
        self._url: str = os.environ.get("A2000_BROWSER_URL", "")
        self._user: str = os.environ.get("A2000_BROWSER_USER", "")
        self._password: str = os.environ.get("A2000_BROWSER_PASS", "")

    async def create_order(self, po: POData) -> OrderResult:
        raise NotImplementedError(
            "Playwright automation requires A2000_BROWSER_URL and screen recording session. "
            "Record the order entry flow and implement selectors here."
        )

    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        raise NotImplementedError("Playwright get_order not yet implemented.")

    async def get_invoice(self, order_id: str) -> bytes:
        raise NotImplementedError("Playwright get_invoice not yet implemented.")

    async def print_order(self, order_id: str) -> bool:
        raise NotImplementedError("Playwright print_order not yet implemented.")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODE_MAP: dict[str, type[A2000ClientBase]] = {
    "mock": MockA2000Client,
    "api": APIA2000Client,
    "edi": EDIA2000Client,
    "playwright": PlaywrightA2000Client,
}


def get_a2000_client(mode: Optional[str] = None) -> A2000ClientBase:
    """
    Return the appropriate A2000 client for the given mode.
    Falls back to A2000_MODE env var, then 'mock'.
    """
    resolved_mode = (mode or os.environ.get("A2000_MODE", "mock")).strip().lower()
    client_class = _MODE_MAP.get(resolved_mode)
    if client_class is None:
        raise ValueError(
            f"Unknown A2000_MODE {resolved_mode!r}. Valid values: {list(_MODE_MAP)}"
        )
    logger.debug("get_a2000_client: instantiating %s", client_class.__name__)
    return client_class()
