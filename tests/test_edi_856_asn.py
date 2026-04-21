"""
tests/test_edi_856_asn.py
--------------------------
Tests for adapters/edi_856_asn.py — X12 5010 EDI 856 Advance Ship Notice builder.

All tests are pure-computation; no network calls, no database, no mocks needed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from adapters.edi_856_asn import (
    ASNBuilder,
    CartonContent,
    PalletContent,
    ShipmentData,
    build_asn,
    write_asn_to_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SHIP_DATE = datetime(2026, 5, 1, 10, 30)

_CARTON_A = CartonContent(
    sscc="000614141000012345",
    gtin="00012345678905",
    upc="012345678905",
    description="Premium Cotton T-Shirt Black M",
    quantity=12,
)

_CARTON_B = CartonContent(
    sscc="000614141000012346",
    gtin="00012345678912",
    upc="012345678912",
    description="Athletic Sock 6-Pack White",
    quantity=6,
)


def _make_shipment(
    pallets: list[PalletContent] | None = None,
    ship_to_name: str = "Walgreens DC Aurora",
) -> ShipmentData:
    if pallets is None:
        pallets = [PalletContent(sscc="000614141999900001", cartons=[_CARTON_A])]
    return ShipmentData(
        asn_number="ASN-2026-001",
        ship_date=_SHIP_DATE,
        bol_number="BOL-987654",
        carrier_scac="FDEG",
        ship_from_name="Emmanuel Apparel Inc",
        ship_from_address={"street": "100 Warehouse Blvd", "city": "Toronto", "state": "ON", "zip": "M5V1A1"},
        ship_to_name=ship_to_name,
        ship_to_address={"street": "5500 Industrial Blvd", "city": "Aurora", "state": "IL", "zip": "60504"},
        ship_to_store_id="DC0042",
        po_number="PO-2026-04567",
        pallets=pallets,
        total_weight_lb=120,
    )


def _parse_segments(edi_bytes: bytes) -> list[list[str]]:
    """Split EDI bytes into a list of [segment_id, element1, ...] lists."""
    text = edi_bytes.decode("utf-8")
    raw = [line.rstrip("~") for line in text.splitlines() if line.strip()]
    return [seg.split("*") for seg in raw if seg]


def _find_segs(segments: list[list[str]], tag: str) -> list[list[str]]:
    return [s for s in segments if s[0] == tag]


# ---------------------------------------------------------------------------
# Structure tests — 1 pallet, 1 carton, 1 item
# ---------------------------------------------------------------------------


def test_build_asn_returns_bytes() -> None:
    edi = build_asn(_make_shipment(), sender_id="MYSENDER", receiver_id="WALGREENS")
    assert isinstance(edi, bytes)
    assert len(edi) > 0


def test_build_asn_contains_required_envelope_segments() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    tags = {s[0] for s in segs}
    for required in ("ISA", "GS", "ST", "BSN", "HL", "CTT", "SE", "GE", "IEA"):
        assert required in tags, f"Missing segment: {required}"


def test_build_asn_st_transaction_set_code_is_856() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    st_segs = _find_segs(segs, "ST")
    assert st_segs, "ST segment missing"
    assert st_segs[0][1] == "856"


def test_build_asn_hl_hierarchy_single_pallet() -> None:
    """1 pallet, 1 carton, 1 item → 5 HL segments: S, O, T, P, I."""
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    hl_segs = _find_segs(segs, "HL")
    assert len(hl_segs) == 5
    hl_types = [s[3] for s in hl_segs]
    assert hl_types == ["S", "O", "T", "P", "I"]


def test_build_asn_sscc_in_man_segment() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    man_segs = _find_segs(segs, "MAN")
    sscc_values = [s[2] for s in man_segs]
    assert "000614141999900001" in sscc_values  # pallet SSCC
    assert "000614141000012345" in sscc_values  # carton SSCC


def test_build_asn_lin_contains_upc() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    lin_segs = _find_segs(segs, "LIN")
    assert lin_segs
    assert lin_segs[0][2] == "UP"
    assert lin_segs[0][3] == "012345678905"


def test_build_asn_sn1_contains_quantity() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    sn1_segs = _find_segs(segs, "SN1")
    assert sn1_segs
    assert sn1_segs[0][2] == "12"
    assert sn1_segs[0][3] == "EA"


# ---------------------------------------------------------------------------
# Multi-pallet / multi-carton tests
# ---------------------------------------------------------------------------


def test_build_asn_two_pallets_four_cartons() -> None:
    """2 pallets × 2 cartons each → 14 HL segments: S, O, T, P, I, T, P, I, T, P, I, T, P, I."""
    pallets = [
        PalletContent(
            sscc="000614141999900001",
            cartons=[_CARTON_A, _CARTON_B],
        ),
        PalletContent(
            sscc="000614141999900002",
            cartons=[_CARTON_A, _CARTON_B],
        ),
    ]
    edi = build_asn(_make_shipment(pallets=pallets), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    hl_segs = _find_segs(segs, "HL")
    # S + O + (T + P + I + P + I) + (T + P + I + P + I) = 2 + 2*5 = 12
    # Actually: 1 S + 1 O + 2*(1 T + 2*(1 P + 1 I)) = 1+1+2*(1+4) = 12
    assert len(hl_segs) == 12


def test_ctt_matches_hl_count_multi_pallet() -> None:
    pallets = [
        PalletContent(sscc="000614141999900001", cartons=[_CARTON_A, _CARTON_B]),
        PalletContent(sscc="000614141999900002", cartons=[_CARTON_A]),
    ]
    edi = build_asn(_make_shipment(pallets=pallets), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    ctt_segs = _find_segs(segs, "CTT")
    hl_segs = _find_segs(segs, "HL")
    assert ctt_segs
    assert int(ctt_segs[0][1]) == len(hl_segs)


# ---------------------------------------------------------------------------
# ISA / control number tests
# ---------------------------------------------------------------------------


def test_isa_control_number_propagates() -> None:
    edi = ASNBuilder("SENDER", "RECEIVER").build(_make_shipment(), control_number=42)
    segs = _parse_segments(edi)
    isa = _find_segs(segs, "ISA")[0]
    assert isa[13] == "000000042"


def test_iea_control_number_matches_isa() -> None:
    edi = ASNBuilder("SENDER", "RECEIVER").build(_make_shipment(), control_number=7)
    segs = _parse_segments(edi)
    isa = _find_segs(segs, "ISA")[0]
    iea = _find_segs(segs, "IEA")[0]
    assert isa[13] == iea[2]


# ---------------------------------------------------------------------------
# SE segment count
# ---------------------------------------------------------------------------


def test_se_segment_count_matches_actual() -> None:
    """SE01 must equal the number of segments from ST through SE inclusive."""
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    text = edi.decode("utf-8")
    lines = [l.rstrip("~") for l in text.splitlines() if l.strip()]

    st_idx = next(i for i, l in enumerate(lines) if l.startswith("ST*"))
    se_idx = next(i for i, l in enumerate(lines) if l.startswith("SE*"))

    expected_count = se_idx - st_idx + 1  # inclusive of both ST and SE
    se_elements = lines[se_idx].split("*")
    assert int(se_elements[1]) == expected_count


# ---------------------------------------------------------------------------
# DTM date format
# ---------------------------------------------------------------------------


def test_dtm_date_format_is_ccyymmdd() -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    segs = _parse_segments(edi)
    dtm_segs = _find_segs(segs, "DTM")
    assert dtm_segs
    date_value = dtm_segs[0][2]
    assert len(date_value) == 8
    assert date_value == "20260501"


# ---------------------------------------------------------------------------
# Field sanitation — long names and special chars
# ---------------------------------------------------------------------------


def test_long_ship_to_name_is_truncated() -> None:
    long_name = "A" * 100
    shipment = _make_shipment(ship_to_name=long_name)
    edi = build_asn(shipment, "SENDER", "RECEIVER")
    segs = _parse_segments(edi)
    n1_st = next(s for s in segs if s[0] == "N1" and s[1] == "ST")
    assert len(n1_st[2]) <= 60


def test_special_chars_stripped_from_ship_to_name() -> None:
    shipment = _make_shipment(ship_to_name="Walgreens*DC~Aurora>Test")
    edi = build_asn(shipment, "SENDER", "RECEIVER")
    segs = _parse_segments(edi)
    n1_st = next(s for s in segs if s[0] == "N1" and s[1] == "ST")
    assert "*" not in n1_st[2]
    assert "~" not in n1_st[2]
    assert ">" not in n1_st[2]


# ---------------------------------------------------------------------------
# Empty pallet guard
# ---------------------------------------------------------------------------


def test_build_asn_raises_on_empty_pallets() -> None:
    shipment = _make_shipment(pallets=[])
    with pytest.raises(ValueError, match="pallets"):
        build_asn(shipment, "SENDER", "RECEIVER")


# ---------------------------------------------------------------------------
# write_asn_to_file
# ---------------------------------------------------------------------------


def test_write_asn_to_file_creates_edi_file(tmp_path: Path) -> None:
    edi = build_asn(_make_shipment(), "MYSENDER", "WALGREENS")
    out = write_asn_to_file(edi, tmp_path, "ASN-2026-001")
    assert out.exists()
    assert out.suffix == ".edi"
    assert out.read_bytes() == edi
