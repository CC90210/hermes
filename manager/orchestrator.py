"""
manager/orchestrator.py
-----------------------
Central coordinator for Hermes.

Pipeline:
    email_received → po_parsed → order_entered → invoice_retrieved → invoice_emailed

Each step advances order status in the DB.  If a step raises, the order stays
at its current status and is retried (or escalated) by handle_failures().
"""

from __future__ import annotations

import asyncio
import html
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from agents.email_agent import EmailAgent  # noqa: E402
from adapters.po_parser import POParser  # noqa: E402
from agents.pos_agent import POSAgent  # noqa: E402
from manager.config import config  # noqa: E402  (after load_dotenv)
from storage.db import (  # noqa: E402
    OrderStatus,
    get_order,
    increment_retry_count,
    init_db,
    list_orders_by_status,
    log_audit,
    update_order_status,
)

logger = logging.getLogger(__name__)

# Maximum consecutive failures before an order is escalated rather than retried
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# A2000 client factory
# ---------------------------------------------------------------------------

def _build_a2000_client(mode: str) -> Any:
    """Return the appropriate A2000 adapter based on A2000_MODE."""
    if mode == "mock":
        from adapters.a2000_mock import A2000MockClient
        return A2000MockClient()
    if mode == "api":
        from adapters.a2000_api import A2000ApiClient
        return A2000ApiClient(
            api_url=config.a2000_api_url,
            api_key=config.a2000_api_key,
        )
    if mode == "edi":
        from adapters.a2000_edi import A2000EdiClient
        return A2000EdiClient()
    if mode == "playwright":
        from adapters.a2000_playwright import A2000PlaywrightClient
        return A2000PlaywrightClient()
    raise ValueError(f"Unknown A2000_MODE: {mode!r}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Ties the email agent, PO parser, and POS agent together."""

    def __init__(self) -> None:
        self._cycle: int = 0
        self._shutdown: asyncio.Event = asyncio.Event()

        # Agents / clients — instantiated here, connected in setup()
        self._email_agent: EmailAgent = EmailAgent(config)
        self._po_parser: POParser = POParser(config)
        self._pos_agent: POSAgent = POSAgent(config)
        self._a2000 = _build_a2000_client(config.a2000_mode)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        """Initialise DB, connect email, validate A2000."""
        logger.info("Initialising database at %s", config.db_path)
        await init_db(config.db_path)

        logger.info("Connecting email agent (%s)", config.email_user)
        await self._email_agent.connect()

        logger.info("Validating A2000 connection (mode=%s)", config.a2000_mode)
        await self._a2000.validate()

        await log_audit(
            config.db_path,
            agent_name="orchestrator",
            action="startup",
            details={"mode": config.a2000_mode, "email": config.email_user},
        )
        logger.info("Orchestrator setup complete.")

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------

    async def run_cycle(self) -> dict[str, int]:
        """Execute one full automation cycle.

        Returns a summary dict: {processed, failed, skipped}.
        """
        self._cycle += 1
        cycle_id = self._cycle
        logger.info("=== Cycle %d start ===", cycle_id)

        processed = 0
        failed = 0

        # Step 1 — poll inbox for new POs
        try:
            new_emails = await self._email_agent.poll_inbox()
            logger.info("Cycle %d: %d new email(s) found", cycle_id, len(new_emails))
        except Exception:
            logger.exception("Cycle %d: email poll failed", cycle_id)
            await log_audit(
                config.db_path,
                agent_name="orchestrator",
                action="cycle_email_poll_error",
                details={"cycle": cycle_id},
            )
            return {"processed": 0, "failed": 0, "skipped": 0}

        # Step 2 — parse each email into a structured PO and persist
        for raw_email in new_emails:
            order_id: int | None = None
            try:
                order_id = await self._po_parser.parse_and_persist(raw_email)
                logger.info("Cycle %d: parsed email → order_id=%d", cycle_id, order_id)
            except Exception:
                logger.exception(
                    "Cycle %d: PO parsing failed for email uid=%s",
                    cycle_id,
                    raw_email.get("uid"),
                )
                failed += 1
                continue

            # Steps 3-5 — enter → retrieve invoice → email invoice
            success = await self._process_order(cycle_id, order_id)
            if success:
                processed += 1
            else:
                failed += 1

        # Also pick up any orders that stalled in previous cycles
        recovered = await self._resume_stalled_orders(cycle_id)
        processed += recovered

        summary = {"processed": processed, "failed": failed, "skipped": 0}
        logger.info("=== Cycle %d complete: %s ===", cycle_id, summary)

        await log_audit(
            config.db_path,
            agent_name="orchestrator",
            action="cycle_complete",
            details={"cycle": cycle_id, **summary},
        )
        return summary

    async def _process_order(self, cycle_id: int, order_id: int) -> bool:
        """Run steps 3-5 for a single order.  Returns True on success."""
        # Step 3 — enter order into A2000
        try:
            await update_order_status(config.db_path, order_id, OrderStatus.ENTERING)
            await self._pos_agent.enter_order(order_id, self._a2000)
            await update_order_status(config.db_path, order_id, OrderStatus.ENTERED)
            logger.debug("Order %d entered into A2000", order_id)
        except Exception:
            logger.exception("Cycle %d: A2000 entry failed for order %d", cycle_id, order_id)
            await update_order_status(config.db_path, order_id, OrderStatus.FAILED)
            return False

        # Step 4 — retrieve invoice from A2000
        try:
            invoice_path = await self._pos_agent.retrieve_invoice(order_id, self._a2000)
            await update_order_status(config.db_path, order_id, OrderStatus.INVOICED)
            logger.debug("Order %d invoice retrieved: %s", order_id, invoice_path)
        except Exception:
            logger.exception("Cycle %d: invoice retrieval failed for order %d", cycle_id, order_id)
            await update_order_status(config.db_path, order_id, OrderStatus.FAILED)
            return False

        # Step 5 — email invoice back to customer
        try:
            await self._send_invoice_for_order(order_id, invoice_path)
            await update_order_status(config.db_path, order_id, OrderStatus.EMAILED)
            logger.info("Order %d: invoice emailed to customer", order_id)
        except Exception:
            logger.exception("Cycle %d: invoice email failed for order %d", cycle_id, order_id)
            await update_order_status(config.db_path, order_id, OrderStatus.FAILED)
            return False

        return True

    async def _send_invoice_for_order(self, order_id: int, invoice_path: Path) -> None:
        """Look up order details and call send_invoice with the correct signature."""
        order = await get_order(config.db_path, order_id)
        if order is None:
            raise ValueError(f"Order {order_id} not found when trying to email invoice")
        customer_email: str = order.get("customer_email") or ""
        po_number: str = order.get("po_number") or "UNKNOWN"
        invoice_num = invoice_path.stem  # filename without extension as invoice ref
        subject = (
            f"Invoice {invoice_num} — PO {po_number} | {config.company_name}"
        )
        body = (
            f"Hi,\n\nPlease find attached invoice {invoice_num} for PO {po_number}.\n\n"
            f"Thank you for your business.\n\n— Hermes (on behalf of {config.company_name})"
        )
        pdf_bytes = invoice_path.read_bytes()
        filename = f"invoice_{invoice_num}.pdf"
        await self._email_agent.send_invoice(
            to=customer_email,
            subject=subject,
            body=body,
            attachment=pdf_bytes,
            filename=filename,
        )

    async def _resume_stalled_orders(self, cycle_id: int) -> int:
        """Re-attempt orders stalled at PARSED or ENTERED from prior cycles."""
        recovered = 0
        for stall_status in (OrderStatus.PARSED, OrderStatus.ENTERED):
            stalled = await list_orders_by_status(config.db_path, stall_status)
            for order in stalled:
                order_id = order["id"]
                logger.info(
                    "Cycle %d: resuming stalled order %d (status=%s)",
                    cycle_id, order_id, stall_status.value,
                )
                if stall_status == OrderStatus.PARSED:
                    success = await self._process_order(cycle_id, order_id)
                else:  # ENTERED — skip step 3, continue from step 4
                    success = await self._resume_from_invoice(cycle_id, order_id)
                if success:
                    recovered += 1
        return recovered

    async def _resume_from_invoice(self, cycle_id: int, order_id: int) -> bool:
        try:
            invoice_path = await self._pos_agent.retrieve_invoice(order_id, self._a2000)
            await update_order_status(config.db_path, order_id, OrderStatus.INVOICED)
            await self._send_invoice_for_order(order_id, invoice_path)
            await update_order_status(config.db_path, order_id, OrderStatus.EMAILED)
            return True
        except Exception:
            logger.exception(
                "Cycle %d: resume-from-invoice failed for order %d", cycle_id, order_id
            )
            await update_order_status(config.db_path, order_id, OrderStatus.FAILED)
            return False

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    async def handle_failures(self) -> None:
        """Review FAILED orders and decide: retry or escalate to Emmanuel."""
        from storage.db import get_audit_log

        failed_orders = await list_orders_by_status(config.db_path, OrderStatus.FAILED)
        if not failed_orders:
            return

        retried = 0
        escalated = 0

        for order in failed_orders:
            order_id = order["id"]
            po_number = order.get("po_number", "unknown")
            customer = order.get("customer_name", "unknown")
            order_retry_count: int = order.get("retry_count", 0)

            if order_retry_count >= _MAX_RETRIES:
                # Check if we already escalated this order to avoid repeating
                existing_logs = await get_audit_log(config.db_path, agent_name="orchestrator", limit=500)
                already_escalated = any(
                    e.get("action") == "escalation_sent"
                    and isinstance(e.get("details_json"), str)
                    and f'"order_id": {order_id}' in e.get("details_json", "")
                    for e in existing_logs
                )
                if already_escalated:
                    logger.info(
                        "handle_failures: order %d already escalated, skipping", order_id
                    )
                    continue
                await self.escalate(
                    order_id=order_id,
                    message=(
                        f"Order #{po_number} (customer: {customer}, id: {order_id}) "
                        f"has failed {order_retry_count} times and requires manual review."
                    ),
                )
                escalated += 1
            else:
                # Increment per-order retry counter and reset status for next cycle
                await increment_retry_count(config.db_path, order_id)
                await update_order_status(config.db_path, order_id, OrderStatus.PARSED)
                await log_audit(
                    config.db_path,
                    agent_name="orchestrator",
                    action="order_retry_queued",
                    details={"order_id": order_id, "po_number": po_number, "retry_count": order_retry_count + 1},
                )
                retried += 1

        logger.info(
            "handle_failures: %d retried, %d escalated", retried, escalated
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> dict[str, Any]:
        """Return subsystem status suitable for logging or HTTP response."""
        email_ok = False
        a2000_ok = False

        try:
            email_ok = await self._email_agent.is_connected()
        except Exception:
            logger.debug("health_check: email agent not reachable", exc_info=True)

        try:
            a2000_ok = await self._a2000.is_reachable()
        except Exception:
            logger.debug("health_check: A2000 not reachable", exc_info=True)

        pending = await list_orders_by_status(config.db_path, OrderStatus.PARSED)
        failed = await list_orders_by_status(config.db_path, OrderStatus.FAILED)

        return {
            "email_connected": email_ok,
            "a2000_reachable": a2000_ok,
            "pending_orders": len(pending),
            "failed_orders": len(failed),
            "cycle_count": self._cycle,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    async def escalate(self, message: str, order_id: int | None = None) -> None:
        """Send an alert email to Emmanuel about an issue requiring attention."""
        escalation_addr = config.escalation_email
        logger.warning("ESCALATION → %s: %s", escalation_addr, message)

        subject = "[Hermes] Action Required"
        safe_message = html.escape(message)
        body = (
            f"<p>Hello Emmanuel,</p>"
            f"<p>Hermes requires your attention:</p>"
            f"<blockquote>{safe_message}</blockquote>"
            f"<p>Timestamp: {datetime.now(timezone.utc).isoformat()}</p>"
            f"<p>— Hermes</p>"
        )

        try:
            await self._email_agent.send_alert(
                to_addr=escalation_addr,
                subject=subject,
                body_html=body,
            )
            await log_audit(
                config.db_path,
                agent_name="orchestrator",
                action="escalation_sent",
                details={"to": escalation_addr, "message": message, "order_id": order_id},
            )
        except Exception:
            logger.exception("Failed to send escalation email to %s", escalation_addr)
            await log_audit(
                config.db_path,
                agent_name="orchestrator",
                action="escalation_failed",
                details={"to": escalation_addr, "message": message, "order_id": order_id},
            )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_forever(self, interval_seconds: int = 300) -> None:
        """Run cycles on a fixed interval until SIGINT or SIGTERM."""
        loop = asyncio.get_running_loop()

        def _request_shutdown(*_: Any) -> None:
            logger.info("Shutdown signal received — finishing current cycle then exiting.")
            self._shutdown.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_shutdown)
            except (NotImplementedError, OSError):
                # Windows does not support add_signal_handler for all signals
                signal.signal(sig, _request_shutdown)  # type: ignore[arg-type]

        logger.info(
            "Orchestrator running — interval=%ds, mode=%s",
            interval_seconds,
            config.a2000_mode,
        )

        while not self._shutdown.is_set():
            loop = asyncio.get_running_loop()
            cycle_start = loop.time()

            try:
                await self.run_cycle()
                await self.handle_failures()
            except Exception:
                logger.exception("Unhandled error in run_cycle — continuing.")

            elapsed = asyncio.get_running_loop().time() - cycle_start
            wait = max(0.0, interval_seconds - elapsed)

            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass  # Normal — interval elapsed, run next cycle

        logger.info("Orchestrator shut down cleanly after %d cycle(s).", self._cycle)
        await log_audit(
            config.db_path,
            agent_name="orchestrator",
            action="shutdown",
            details={"cycles_completed": self._cycle},
        )
