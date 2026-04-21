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

from dataclasses import dataclass, field


@dataclass
class CartonContent:
    """Represents the contents of a single physical shipping carton.

    The SSCC and every GTIN in this record must match the physical GS1-128
    label printed on the carton. Any mismatch generates an automatic chargeback.

    Attributes
    ----------
    sscc:
        18-digit Serial Shipping Container Code, computed by
        :func:`gs1_128_label.compute_sscc`. Includes the leading Application
        Identifier (00) in some label contexts but is stored here as the
        18-digit numeric string only.
    gtin:
        14-digit Global Trade Item Number (GTIN-14) of the product packed in
        this carton. Derived from the item's UPC-12 with leading zeros.
    qty:
        Number of eaches of ``gtin`` packed in this carton.
    po_number:
        Purchase order number this carton fulfills.
    line_seq:
        The PO line sequence number being fulfilled by this carton.
    """

    sscc: str
    gtin: str
    qty: int
    po_number: str
    line_seq: int
    weight_lbs: float = 0.0
    carton_number: int = 1
    total_cartons: int = 1


class ASNBuilder:
    """Builds a hierarchical ANSI X12 5010 EDI 856 Advance Ship Notice.

    The X12 856 uses a mandatory HL (Hierarchical Level) loop structure:
        Shipment (S)  →  Order (O)  →  Tare (T)  →  Pack (P)  →  Item (I)

    Each level is an HL segment with a parent reference. This class maintains
    state across :meth:`add_carton` calls and produces the full envelope on
    :meth:`build_asn`.

    Usage::

        builder = ASNBuilder(
            shipment_id="SHIP-2026-001",
            ship_date="2026-05-01",
            carrier_scac="UPSN",
            pro_number="1Z999AA10123456784",
        )
        builder.add_carton(CartonContent(sscc="000123456789012347", ...))
        edi_bytes = builder.build_asn()
    """

    def __init__(
        self,
        shipment_id: str,
        ship_date: str,
        carrier_scac: str,
        pro_number: str,
    ) -> None:
        """Initialise ASN builder for a single shipment.

        Parameters
        ----------
        shipment_id:
            Internal shipment reference (becomes BSN02 in the 856 envelope).
        ship_date:
            ISO-8601 date the shipment departs the dock (YYYYMMDD for X12).
        carrier_scac:
            Standard Carrier Alpha Code (e.g. "UPSN", "FXFE").
        pro_number:
            Carrier tracking / PRO number for the shipment.
        """
        raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")

    def add_carton(self, carton: CartonContent) -> None:
        """Append a single carton to the ASN being built.

        Must be called once per physical carton before :meth:`build_asn`.
        The SSCC in ``carton`` will be included in the HL-Tare segment; the
        GTIN and quantity appear in the LIN/SN1 item segments.

        Parameters
        ----------
        carton:
            Fully populated :class:`CartonContent` for the carton.
        """
        raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")

    def build_asn(self) -> bytes:
        """Serialise the accumulated carton data into a complete X12 856.

        Returns
        -------
        bytes
            Raw EDI X12 byte string including ISA/GS/ST/BSN/HL loops/SE/GE/IEA.
            Ready for transmission to VAN or AS2 endpoint.

        Raises
        ------
        ValueError
            If no cartons have been added, or mandatory fields (ship_date,
            carrier_scac) are missing.
        NotImplementedError
            Until Phase 2b implementation is complete.
        """
        raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")


def build_asn(order_id: int, packing_list: list[CartonContent]) -> bytes:
    """Convenience wrapper: build an 856 ASN from an order ID and packing list.

    Loads shipment metadata from the local SQLite database by ``order_id``,
    constructs an :class:`ASNBuilder`, adds all cartons, and returns the
    serialised X12 bytes.

    Parameters
    ----------
    order_id:
        Hermes internal order ID as stored in the SQLite ``orders`` table.
    packing_list:
        One :class:`CartonContent` per physical carton being shipped.

    Returns
    -------
    bytes
        Complete EDI 856 document ready for transmission.

    Raises
    ------
    ValueError
        If the order does not exist or is missing mandatory ship fields.
    NotImplementedError
        Until Phase 2b implementation is complete.
    """
    raise NotImplementedError("Phase 2b — see docs/BUILD_PLAN.md")
