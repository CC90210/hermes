from __future__ import annotations

import logging
import pathlib
from typing import Any

from adapters.po_parser import POData
from storage.db import (
    get_order,
    get_order_lines,
    log_audit,
    update_order_status,
    OrderStatus,
)

logger = logging.getLogger(__name__)


class POSAgent:
    """Enters purchase orders into A2000 and retrieves invoices.

    The constructor takes only ``config``; the A2000 client is passed per-call
    so the orchestrator can swap or mock it independently.
    """

    def __init__(self, config: Any) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_po(self, po: POData) -> list[str]:
        errors: list[str] = []
        if not po.po_number:
            errors.append("po_number is required")
        if not po.line_items:
            errors.append("line_items must not be empty")
        return errors

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    async def enter_order(self, order_id: int, a2000_client: Any) -> None:
        """Look up ``order_id`` from DB, reconstruct POData, submit to A2000.

        Updates the order status to ENTERED on success or FAILED on error.
        Raises on failure so the orchestrator can catch and handle it.
        """
        db_path = self._config.db_path
        row = await get_order(db_path, order_id)
        if row is None:
            raise ValueError(f"Order {order_id} not found in database")

        lines = await get_order_lines(db_path, order_id)

        from adapters.po_parser import LineItem
        po = POData(
            po_number=row.get("po_number"),
            customer_name=row.get("customer_name"),
            customer_email=row.get("customer_email"),
            customer_address=row.get("customer_address"),
            ship_to_address=row.get("ship_to_address"),
            order_date=row.get("order_date"),
            ship_date=row.get("ship_date"),
            notes=row.get("notes"),
            raw_text=row.get("raw_text", ""),
            internal_order_id=str(order_id),
            line_items=[
                LineItem(
                    sku=line.get("sku") or None,
                    description=line.get("description") or "",
                    quantity=int(line.get("quantity") or 0),
                    unit_price=float(line.get("unit_price") or 0.0),
                )
                for line in lines
            ],
        )

        errors = self._validate_po(po)
        if errors:
            msg = "; ".join(errors)
            await update_order_status(db_path, order_id, OrderStatus.FAILED)
            await log_audit(
                db_path,
                agent_name="pos_agent",
                action="validation_failed",
                details={"order_id": order_id, "errors": msg},
            )
            raise ValueError(f"PO validation failed for order {order_id}: {msg}")

        await log_audit(
            db_path,
            agent_name="pos_agent",
            action="entering",
            details={"order_id": order_id, "po_number": po.po_number},
        )
        logger.info("Entering order_id=%s (po_number=%s) into A2000", order_id, po.po_number)

        await a2000_client.create_order(po)

        await log_audit(
            db_path,
            agent_name="pos_agent",
            action="entered",
            details={"order_id": order_id},
        )
        logger.info("order_id=%s entered into A2000", order_id)

    async def retrieve_invoice(self, order_id: int, a2000_client: Any) -> pathlib.Path:
        """Fetch invoice bytes from A2000 and write to disk.

        Returns the ``pathlib.Path`` of the saved PDF.
        Raises on failure so the orchestrator can catch and handle it.
        """
        db_path = self._config.db_path
        logger.info("Retrieving invoice for order_id=%s", order_id)

        pdf_bytes: bytes = await a2000_client.get_invoice(str(order_id))

        invoice_dir = pathlib.Path(self._config.log_dir) / "invoices"
        invoice_dir.mkdir(parents=True, exist_ok=True)
        invoice_path = invoice_dir / f"{order_id}.pdf"
        invoice_path.write_bytes(pdf_bytes)

        await log_audit(
            db_path,
            agent_name="pos_agent",
            action="invoice_retrieved",
            details={"order_id": order_id, "path": str(invoice_path), "size": len(pdf_bytes)},
        )
        logger.info("Invoice for order_id=%s saved to %s (%d bytes)", order_id, invoice_path, len(pdf_bytes))
        return invoice_path

    # ------------------------------------------------------------------
    # Legacy / standalone helpers (kept for backward compat)
    # ------------------------------------------------------------------

    async def print_order(self, order_id: str, a2000_client: Any) -> bool:
        logger.info("Sending print command for order_id=%s", order_id)
        try:
            success = await a2000_client.print_order(order_id)
        except Exception:
            logger.exception("print_order failed for order_id=%s", order_id)
            return False

        logger.info("print_order order_id=%s → success=%s", order_id, success)
        return success
