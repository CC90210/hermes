"""EDI 855 Purchase Order Acknowledgment generator.

Implements Phase 3b — PO Acknowledgment (PRE-LAUNCH).

Walgreens requires an EDI 855 response within 24–48 hours of every 850 PO receipt.
Missing this window flags the vendor in Walgreens' compliance system before the first
shipment ever leaves the dock.

Three response modes:
  - AE (accept as-is): clean PO, all line items confirmed
  - AT (accept with changes): some lines modified
  - RD (reject): invalid SKU, credit hold, or structurally unprocessable PO

Reference: docs/WHOLESALE_RESEARCH.md — Section 2 (Walgreens Vendor Compliance),
           lifecycle Stage 3 (PO Acknowledgment).
ANSI X12 Version 5010, Transaction Set 855.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

from adapters.po_parser import LineItem, POData

_log = logging.getLogger(__name__)


class AckMode(str, Enum):
    ACCEPT_AS_IS = "AE"
    ACCEPT_WITH_CHANGES = "AT"
    REJECT = "RD"


class LineAckCode(str, Enum):
    ACCEPT_AS_IS = "IA"
    BACKORDER = "IB"
    PRICE_CHANGE = "IP"
    REJECT_LINE = "IR"
    QUANTITY_CHANGE = "IQ"


@dataclass
class LineAck:
    line_number: int
    sku: str
    original_qty: int
    ack_code: LineAckCode
    accepted_qty: Optional[int] = None
    accepted_price: Optional[Decimal] = None
    ship_date: Optional[date] = None
    note: Optional[str] = None


@dataclass
class AckData:
    po_number: str
    po_date: date
    vendor_order_number: str
    mode: AckMode
    line_acks: list[LineAck] = field(default_factory=list)
    ship_to_name: str = ""
    bill_to_name: str = ""
    requested_ship_date: Optional[date] = None


class Ack855Builder:
    """Builds a complete ANSI X12 5010 EDI 855 PO Acknowledgment document."""

    def __init__(self, sender_id: str, receiver_id: str) -> None:
        self._sender = sender_id.ljust(15)[:15]
        self._receiver = receiver_id.ljust(15)[:15]

    def build(self, ack: AckData, control_number: int = 1) -> bytes:
        """Build and return the complete 855 as EDI bytes."""
        segments: list[str] = []
        segments.append(self._build_isa(control_number))
        segments.append(self._build_gs(control_number))
        segments.append(f"ST*855*{control_number:04d}")
        segments.append(self._build_bak(ack))

        if ack.vendor_order_number:
            segments.append(f"REF*VN*{ack.vendor_order_number}")

        if ack.requested_ship_date:
            segments.append(f"DTM*002*{ack.requested_ship_date.strftime('%Y%m%d')}")

        if ack.ship_to_name:
            segments.append(f"N1*ST*{ack.ship_to_name}")

        if ack.bill_to_name:
            segments.append(f"N1*BT*{ack.bill_to_name}")

        for line in ack.line_acks:
            segments.extend(self._build_line_ack(line))

        segments.append(f"CTT*{len(ack.line_acks)}")

        # SE segment count includes ST and SE themselves
        # Everything between ST and SE is counted
        st_index = next(i for i, s in enumerate(segments) if s.startswith("ST*"))
        # segments after ST (exclusive) up to but not including SE
        body_count = len(segments) - st_index + 1  # +1 for SE itself
        segments.append(f"SE*{body_count}*{control_number:04d}")

        segments.append(f"GE*1*{control_number}")
        segments.append(f"IEA*1*{control_number:09d}")

        raw = "~\n".join(segments) + "~\n"
        return raw.encode("ascii")

    def _build_isa(self, control_number: int) -> str:
        now = datetime.utcnow()
        date_str = now.strftime("%y%m%d")
        time_str = now.strftime("%H%M")
        ctrl = f"{control_number:09d}"
        return (
            f"ISA*00*          *00*          "
            f"*ZZ*{self._sender}*ZZ*{self._receiver}"
            f"*{date_str}*{time_str}*^*00501*{ctrl}*0*P*>"
        )

    def _build_gs(self, control_number: int) -> str:
        now = datetime.utcnow()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M")
        sender = self._sender.strip()
        receiver = self._receiver.strip()
        return (
            f"GS*PR*{sender}*{receiver}"
            f"*{date_str}*{time_str}*{control_number}*X*005010"
        )

    def _build_bak(self, ack: AckData) -> str:
        po_date_str = ack.po_date.strftime("%Y%m%d")
        return f"BAK*00*{ack.mode.value}*{ack.po_number}*{po_date_str}"

    def _build_line_ack(self, line: LineAck) -> list[str]:
        segs: list[str] = []
        qty = line.accepted_qty if line.accepted_qty is not None else line.original_qty
        price_str = ""
        if line.accepted_price is not None:
            price_str = f"*PE*{line.accepted_price}"

        uom = "EA"
        ship_date_str = ""
        if line.ship_date:
            ship_date_str = f"*IS*{line.ship_date.strftime('%Y%m%d')}"

        sku_str = f"*BP*{line.sku}" if line.sku else ""
        segs.append(
            f"PO1*{line.line_number}*{line.original_qty}*{uom}"
            f"**PE{sku_str}"
        )
        segs.append(
            f"ACK*{line.ack_code.value}*{qty}*{uom}{ship_date_str}"
        )
        return segs


# ---------------------------------------------------------------------------
# Public convenience API
# ---------------------------------------------------------------------------

def build_855(ack: AckData, sender_id: str, receiver_id: str) -> bytes:
    """Convenience: build a full 855 document."""
    return Ack855Builder(sender_id, receiver_id).build(ack)


def from_po_auto_accept(
    po: POData,
    vendor_order_number: str,
    ship_date: date,
    sender_id: str,
    receiver_id: str,
) -> bytes:
    """Generate an 'accept all lines as-is' 855 from a parsed PO."""
    po_date = _parse_date(po.order_date) or date.today()
    line_acks = [
        LineAck(
            line_number=i + 1,
            sku=item.sku or "",
            original_qty=item.quantity,
            ack_code=LineAckCode.ACCEPT_AS_IS,
            ship_date=ship_date,
        )
        for i, item in enumerate(po.line_items)
    ]
    ack = AckData(
        po_number=po.po_number or "",
        po_date=po_date,
        vendor_order_number=vendor_order_number,
        mode=AckMode.ACCEPT_AS_IS,
        line_acks=line_acks,
        ship_to_name=po.ship_to_address or "",
        bill_to_name=po.customer_name or "",
        requested_ship_date=ship_date,
    )
    return build_855(ack, sender_id, receiver_id)


def from_po_with_changes(
    po: POData,
    vendor_order_number: str,
    line_decisions: list[LineAck],
    sender_id: str,
    receiver_id: str,
) -> bytes:
    """Generate an 855 with per-line decisions — some accept, some change, some reject."""
    po_date = _parse_date(po.order_date) or date.today()

    all_reject = all(la.ack_code == LineAckCode.REJECT_LINE for la in line_decisions)
    all_accept = all(la.ack_code == LineAckCode.ACCEPT_AS_IS for la in line_decisions)

    if all_reject:
        mode = AckMode.REJECT
    elif all_accept:
        mode = AckMode.ACCEPT_AS_IS
    else:
        mode = AckMode.ACCEPT_WITH_CHANGES

    ack = AckData(
        po_number=po.po_number or "",
        po_date=po_date,
        vendor_order_number=vendor_order_number,
        mode=mode,
        line_acks=line_decisions,
        ship_to_name=po.ship_to_address or "",
        bill_to_name=po.customer_name or "",
    )
    return build_855(ack, sender_id, receiver_id)


def write_855_to_file(edi_bytes: bytes, output_dir: Path, po_number: str) -> Path:
    """Write 855 to disk: {po_number}_855_{timestamp}.edi"""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_po = po_number.replace("/", "-").replace("\\", "-")
    path = output_dir / f"{safe_po}_855_{ts}.edi"
    path.write_bytes(edi_bytes)
    _log.info("Wrote 855 to %s (%d bytes)", path, len(edi_bytes))
    return path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Legacy shim — keeps existing callers that used generate_855 / transmit_855
# ---------------------------------------------------------------------------

def generate_855(po: POData, mode: str, changes: dict | None = None) -> bytes:
    """Legacy shim: wrap the new typed API for callers using the old signature."""
    if mode == "accept":
        ship_date = _parse_date(po.ship_date) or date.today()
        return from_po_auto_accept(po, "AUTO", ship_date, "VENDOR", "WALGREENS")
    if mode == "reject":
        po_date = _parse_date(po.order_date) or date.today()
        line_acks = [
            LineAck(
                line_number=i + 1,
                sku=item.sku or "",
                original_qty=item.quantity,
                ack_code=LineAckCode.REJECT_LINE,
            )
            for i, item in enumerate(po.line_items)
        ]
        ack = AckData(
            po_number=po.po_number or "",
            po_date=po_date,
            vendor_order_number="AUTO",
            mode=AckMode.REJECT,
            line_acks=line_acks,
        )
        return build_855(ack, "VENDOR", "WALGREENS")
    if mode == "change":
        if not changes:
            raise ValueError("changes dict is required when mode='change'")
        ship_date = _parse_date(po.ship_date) or date.today()
        line_map: dict[int, dict] = {
            lc["line_seq"]: lc for lc in (changes.get("lines") or [])
        }
        po_date = _parse_date(po.order_date) or date.today()
        line_acks = []
        for i, item in enumerate(po.line_items):
            seq = i + 1
            lc = line_map.get(seq, {})
            ack_qty = lc.get("acknowledged_qty")
            ack_price_raw = lc.get("acknowledged_price")
            ack_price = Decimal(str(ack_price_raw)) if ack_price_raw is not None else None
            ack_date_str = lc.get("ship_date")
            ack_date = _parse_date(ack_date_str) if ack_date_str else ship_date

            if ack_qty is not None and ack_qty != item.quantity:
                code = LineAckCode.QUANTITY_CHANGE
            elif ack_price is not None and ack_price != Decimal(str(item.unit_price)):
                code = LineAckCode.PRICE_CHANGE
            else:
                code = LineAckCode.ACCEPT_AS_IS

            line_acks.append(
                LineAck(
                    line_number=seq,
                    sku=item.sku or "",
                    original_qty=item.quantity,
                    ack_code=code,
                    accepted_qty=ack_qty,
                    accepted_price=ack_price,
                    ship_date=ack_date,
                )
            )
        ack = AckData(
            po_number=po.po_number or "",
            po_date=po_date,
            vendor_order_number="AUTO",
            mode=AckMode.ACCEPT_WITH_CHANGES,
            line_acks=line_acks,
        )
        return build_855(ack, "VENDOR", "WALGREENS")
    raise ValueError(f"Unknown mode: {mode!r}")


def transmit_855(edi_bytes: bytes, va_target: str) -> bool:
    """Stub: actual VAN/AS2 transmission is out of scope for Phase 3b."""
    _log.info("transmit_855: %d bytes → %s (stub — configure VAN for real transmission)", len(edi_bytes), va_target)
    return True
