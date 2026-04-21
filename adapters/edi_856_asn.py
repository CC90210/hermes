"""EDI 856 Advance Ship Notice (ASN) generator.

Implements Phase 2b — ASN + Carton Labels (PRE-LAUNCH FOR WALGREENS).

The ASN is the single most critical compliance document in a Walgreens shipment.
Walgreens' Cost Recovery Program automatically fines vendors for:
  - ASN arriving after the transmission window (4 hrs DC / 1 hr DSD)
  - SSCC-18 data in the ASN not matching the physical carton label exactly

This module generates the hierarchical X12 856 structure and manages
transmission timing against the configured ship window.

Reference: docs/WHOLESALE_RESEARCH.md — Section 2 (Walgreens Vendor Compliance),
           lifecycle Stage 11 (ASN Generation and Transmission).
ANSI X12 Version 5010, Transaction Set 856.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# X12 5010 delimiters
_ELEM = "*"
_SEG = "~"
_SUB = ">"

# GS1 segment hierarchy type codes
_HL_SHIPMENT = "S"
_HL_ORDER = "O"
_HL_TARE = "T"
_HL_PACK = "P"
_HL_ITEM = "I"

# X12 field max lengths (per 5010 spec)
_MAX_NAME = 60
_MAX_ADDRESS = 55
_MAX_CITY = 30
_MAX_STATE = 2
_MAX_ZIP = 10


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CartonContent:
    """Represents the contents of a single physical shipping carton.

    The SSCC and every GTIN in this record must match the physical GS1-128
    label printed on the carton. Any mismatch generates an automatic chargeback.

    Attributes
    ----------
    sscc:
        18-digit Serial Shipping Container Code, computed by
        :func:`gs1_128_label.compute_sscc`. Stored as 18-digit numeric string.
    gtin:
        14-digit Global Trade Item Number (GTIN-14) of the product packed in
        this carton.
    upc:
        12-digit UPC (GTIN-14 with leading '00' stripped, or last 12 digits).
    description:
        Human-readable item description (truncated to 80 chars in segments).
    quantity:
        Number of eaches packed in this carton.
    unit_of_measure:
        Unit of measure qualifier; default "EA" (each).
    """

    sscc: str
    gtin: str
    upc: str
    description: str
    quantity: int
    unit_of_measure: str = "EA"


@dataclass
class PalletContent:
    """Represents a single pallet (Tare) in the shipment.

    Attributes
    ----------
    sscc:
        18-digit pallet SSCC.
    cartons:
        All cartons strapped to this pallet.
    """

    sscc: str
    cartons: list[CartonContent]


@dataclass
class ShipmentData:
    """Complete data required to generate a single X12 5010 EDI 856 ASN.

    Attributes
    ----------
    asn_number:
        Internal ASN reference; maps to BSN02.
    ship_date:
        Datetime the shipment departs the dock.
    bol_number:
        Bill of Lading number for the carrier.
    carrier_scac:
        Standard Carrier Alpha Code (e.g. "FDEG" for FedEx Ground, "UPSN").
    ship_from_name:
        Legal entity name of the shipper.
    ship_from_address:
        Dict with keys: street, city, state, zip.
    ship_to_name:
        Name of the receiving DC or store.
    ship_to_address:
        Dict with keys: street, city, state, zip.
    ship_to_store_id:
        Walgreens DC or store identifier (used in N1*ST qualifier).
    po_number:
        Purchase Order number being fulfilled.
    pallets:
        Ordered list of pallets in this shipment.
    total_weight_lb:
        Gross shipment weight in pounds.
    """

    asn_number: str
    ship_date: datetime
    bol_number: str
    carrier_scac: str
    ship_from_name: str
    ship_from_address: dict
    ship_to_name: str
    ship_to_address: dict
    ship_to_store_id: str
    po_number: str
    pallets: list[PalletContent]
    total_weight_lb: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitise(value: str, max_len: int) -> str:
    """Strip X12 delimiter characters and truncate to ``max_len``."""
    cleaned = re.sub(r"[*~>]", "", value)
    return cleaned[:max_len]


def _seg(*elements: str) -> str:
    """Join elements with the element separator and append segment terminator."""
    return _ELEM.join(elements) + _SEG


def _date8(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def _date6(dt: datetime) -> str:
    return dt.strftime("%y%m%d")


def _time4(dt: datetime) -> str:
    return dt.strftime("%H%M")


# ---------------------------------------------------------------------------
# ASNBuilder
# ---------------------------------------------------------------------------


class ASNBuilder:
    """Builds a hierarchical ANSI X12 5010 EDI 856 Advance Ship Notice.

    The X12 856 uses a mandatory HL (Hierarchical Level) loop structure::

        Shipment (S)  →  Order (O)  →  Tare (T)  →  Pack (P)  →  Item (I)

    Instantiate with sender/receiver IDs, call :meth:`build` with a populated
    :class:`ShipmentData`, and receive back the complete X12 byte string.

    Usage::

        builder = ASNBuilder("MYSENDERID", "WALGREENS")
        edi_bytes = builder.build(shipment_data, control_number=1)
    """

    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        config: Optional[dict] = None,
    ) -> None:
        self._sender = sender_id.ljust(15)[:15]
        self._receiver = receiver_id.ljust(15)[:15]
        self._config = config or {}

    def build(self, shipment: ShipmentData, control_number: int = 1) -> bytes:
        """Generate a complete X12 5010 856 ASN document.

        Parameters
        ----------
        shipment:
            Fully populated :class:`ShipmentData`.
        control_number:
            ISA13 interchange control number (1–999999999). Caller is
            responsible for incrementing across sessions.

        Returns
        -------
        bytes
            UTF-8 encoded X12 856 document. Segments are newline-separated for
            human readability; segment terminator `~` is always present.
        """
        if not shipment.pallets:
            raise ValueError("ShipmentData.pallets must not be empty")

        segments: list[str] = []
        now = shipment.ship_date

        isa = self._build_isa(control_number, now)
        segments.append(isa)
        segments.append(self._build_gs(control_number, now))
        segments.append(_seg("ST", "856", "0001"))
        segments.append(
            _seg("BSN", "00", shipment.asn_number, _date8(now), _time4(now), "0001")
        )

        hl_counter = 0
        hl_segments: list[str] = []

        # --- Shipment-level HL ---
        shipment_segs, hl_counter = self._build_shipment_hl(shipment, hl_counter)
        hl_segments.extend(shipment_segs)
        shipment_hl_id = 1  # always 1

        # --- Order-level HL ---
        order_segs, hl_counter = self._build_order_hl(
            shipment.po_number, hl_counter, shipment_hl_id
        )
        hl_segments.extend(order_segs)
        order_hl_id = hl_counter - len(order_segs) + 1  # id of the HL*O segment

        for pallet in shipment.pallets:
            tare_segs, hl_counter = self._build_tare_hl(pallet, hl_counter, order_hl_id)
            hl_segments.extend(tare_segs)
            tare_hl_id = hl_counter - len(tare_segs) + 1

            for carton in pallet.cartons:
                pack_segs, hl_counter = self._build_pack_hl(
                    carton, hl_counter, tare_hl_id
                )
                hl_segments.extend(pack_segs)
                pack_hl_id = hl_counter - len(pack_segs) + 1

                item_segs, hl_counter = self._build_item_hl(
                    carton, hl_counter, pack_hl_id
                )
                hl_segments.extend(item_segs)

        segments.extend(hl_segments)

        total_hl = hl_counter
        segments.append(_seg("CTT", str(total_hl)))

        # SE segment count = segments from ST through SE inclusive.
        # segments currently holds: ISA(0), GS(1), ST(2), BSN(3), ...HL..., CTT
        # ST is at index 2, so segments from ST to end = len(segments) - 2.
        # Adding SE itself gives len(segments) - 2 + 1 = len(segments) - 1.
        seg_count = len(segments) - 1  # excludes ISA and GS; includes ST and SE
        segments.append(_seg("SE", str(seg_count), "0001"))
        segments.append(_seg("GE", "1", str(control_number)))
        segments.append(_seg("IEA", "1", str(control_number).zfill(9)))

        return "\n".join(segments).encode("ascii", errors="replace")

    # ------------------------------------------------------------------
    # Private segment builders
    # ------------------------------------------------------------------

    def _build_isa(self, control_number: int, now: datetime) -> str:
        """Build the ISA interchange control header."""
        return _seg(
            "ISA",
            "00",
            "          ",  # ISA02 — auth info (10 chars)
            "00",
            "          ",  # ISA04 — security info (10 chars)
            "ZZ",
            self._sender,
            "ZZ",
            self._receiver,
            _date6(now),
            _time4(now),
            "^",           # component element separator
            "00501",
            str(control_number).zfill(9),
            "0",           # acknowledgment requested: no
            "P",           # usage indicator: production
            _SUB,          # sub-element separator
        )

    def _build_gs(self, control_number: int, now: datetime) -> str:
        """Build the GS functional group header."""
        return _seg(
            "GS",
            "SH",           # functional identifier: ship notice
            self._sender.strip(),
            self._receiver.strip(),
            _date8(now),
            _time4(now),
            str(control_number),
            "X",
            "005010",
        )

    def _build_shipment_hl(
        self, shipment: ShipmentData, hl_counter: int
    ) -> tuple[list[str], int]:
        """Build the Shipment-level HL loop segments (HL*S)."""
        hl_counter += 1
        hl_id = hl_counter
        segs: list[str] = []

        segs.append(_seg("HL", str(hl_id), "", _HL_SHIPMENT))

        pallet_count = len(shipment.pallets)
        segs.append(
            _seg(
                "TD1",
                "PLT94",
                str(pallet_count),
                "", "", "",
                "G",
                str(shipment.total_weight_lb),
                "LB",
            )
        )
        segs.append(_seg("TD5", "", "2", shipment.carrier_scac, "M"))
        segs.append(_seg("REF", "BM", _sanitise(shipment.bol_number, 30)))
        segs.append(
            _seg("DTM", "011", _date8(shipment.ship_date), _time4(shipment.ship_date))
        )

        # Ship-To party
        to_name = _sanitise(shipment.ship_to_name, _MAX_NAME)
        segs.append(_seg("N1", "ST", to_name, "92", _sanitise(shipment.ship_to_store_id, 20)))
        segs.append(_seg("N3", _sanitise(shipment.ship_to_address.get("street", ""), _MAX_ADDRESS)))
        segs.append(
            _seg(
                "N4",
                _sanitise(shipment.ship_to_address.get("city", ""), _MAX_CITY),
                _sanitise(shipment.ship_to_address.get("state", ""), _MAX_STATE),
                _sanitise(shipment.ship_to_address.get("zip", ""), _MAX_ZIP),
            )
        )

        # Ship-From party
        from_name = _sanitise(shipment.ship_from_name, _MAX_NAME)
        segs.append(_seg("N1", "SF", from_name, "92", ""))
        segs.append(_seg("N3", _sanitise(shipment.ship_from_address.get("street", ""), _MAX_ADDRESS)))
        segs.append(
            _seg(
                "N4",
                _sanitise(shipment.ship_from_address.get("city", ""), _MAX_CITY),
                _sanitise(shipment.ship_from_address.get("state", ""), _MAX_STATE),
                _sanitise(shipment.ship_from_address.get("zip", ""), _MAX_ZIP),
            )
        )

        return segs, hl_counter

    def _build_order_hl(
        self, po_number: str, hl_counter: int, parent_id: int
    ) -> tuple[list[str], int]:
        """Build the Order-level HL loop (HL*O)."""
        hl_counter += 1
        segs: list[str] = [
            _seg("HL", str(hl_counter), str(parent_id), _HL_ORDER),
            _seg("PRF", _sanitise(po_number, 22), "", "", ""),
        ]
        return segs, hl_counter

    def _build_tare_hl(
        self, pallet: PalletContent, hl_counter: int, parent_id: int
    ) -> tuple[list[str], int]:
        """Build the Tare-level HL loop for a pallet (HL*T)."""
        hl_counter += 1
        segs: list[str] = [
            _seg("HL", str(hl_counter), str(parent_id), _HL_TARE),
            _seg("MAN", "GM", pallet.sscc),
        ]
        return segs, hl_counter

    def _build_pack_hl(
        self, carton: CartonContent, hl_counter: int, parent_id: int
    ) -> tuple[list[str], int]:
        """Build the Pack-level HL loop for a carton (HL*P)."""
        hl_counter += 1
        segs: list[str] = [
            _seg("HL", str(hl_counter), str(parent_id), _HL_PACK),
            _seg("MAN", "GM", carton.sscc),
        ]
        return segs, hl_counter

    def _build_item_hl(
        self, carton: CartonContent, hl_counter: int, parent_id: int
    ) -> tuple[list[str], int]:
        """Build the Item-level HL loop for the product inside a carton (HL*I)."""
        hl_counter += 1
        desc = _sanitise(carton.description, 80)
        segs: list[str] = [
            _seg("HL", str(hl_counter), str(parent_id), _HL_ITEM),
            _seg("LIN", "", "UP", carton.upc),
            _seg("SN1", "", str(carton.quantity), carton.unit_of_measure),
            _seg("PID", "F", "", "", "", desc),
        ]
        return segs, hl_counter


# ---------------------------------------------------------------------------
# Public convenience functions
# ---------------------------------------------------------------------------


def build_asn(shipment: ShipmentData, sender_id: str, receiver_id: str) -> bytes:
    """Convenience function — instantiates :class:`ASNBuilder` and calls build().

    Parameters
    ----------
    shipment:
        Fully populated :class:`ShipmentData`.
    sender_id:
        ISA06 sender identifier (your company's EDI ID).
    receiver_id:
        ISA08 receiver identifier (trading partner's EDI ID).

    Returns
    -------
    bytes
        Complete X12 5010 EDI 856 document, UTF-8 encoded.
    """
    return ASNBuilder(sender_id, receiver_id).build(shipment)


def write_asn_to_file(edi_bytes: bytes, output_dir: Path, asn_number: str) -> Path:
    """Write an ASN document to disk.

    Parameters
    ----------
    edi_bytes:
        Raw EDI bytes as returned by :func:`build_asn`.
    output_dir:
        Directory to write the file into. Created if it does not exist.
    asn_number:
        Used to build the filename (non-alphanumeric chars replaced with ``-``).

    Returns
    -------
    Path
        Absolute path of the file that was written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_asn = re.sub(r"[^A-Za-z0-9_-]", "-", asn_number)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{safe_asn}_{timestamp}.edi"
    out_path = output_dir / filename
    out_path.write_bytes(edi_bytes)
    return out_path
