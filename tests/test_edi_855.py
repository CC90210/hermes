"""Tests for adapters/edi_855_ack.py — EDI 855 PO Acknowledgment generator."""

from __future__ import annotations

from datetime import date


from adapters.edi_855_ack import (
    AckData,
    AckMode,
    LineAck,
    LineAckCode,
    build_855,
    from_po_auto_accept,
    from_po_with_changes,
)
from adapters.po_parser import LineItem, POData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENDER = "VENDORID"
_RECEIVER = "WALGREENS"


def _make_po(n_lines: int = 3) -> POData:
    return POData(
        po_number="PO-TEST-001",
        customer_name="Walgreens #04231",
        customer_email=None,
        customer_address="Chicago IL",
        ship_to_address="Aurora IL DC",
        order_date="2026-04-15",
        ship_date="2026-05-01",
        line_items=[
            LineItem(sku=f"SKU-{i:03d}", description=f"Item {i}", quantity=100, unit_price=5.00)
            for i in range(1, n_lines + 1)
        ],
    )


def _parse_segments(edi_bytes: bytes) -> dict[str, list[list[str]]]:
    """Return a dict of tag → list of segment element lists."""
    raw = edi_bytes.decode("ascii")
    segment_sep = raw[105]
    element_sep = raw[3]
    result: dict[str, list[list[str]]] = {}
    for seg in raw.split(segment_sep):
        seg = seg.strip()
        if not seg:
            continue
        els = seg.split(element_sep)
        tag = els[0].strip()
        result.setdefault(tag, []).append(els)
    return result


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_855_envelope_present() -> None:
    """ISA, GS, ST, BAK, CTT, SE, GE, IEA are all present."""
    po = _make_po()
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    for required in ("ISA", "GS", "ST", "BAK", "CTT", "SE", "GE", "IEA"):
        assert required in segs, f"Missing segment: {required}"


def test_855_transaction_set_code() -> None:
    """ST segment must have transaction set code 855."""
    po = _make_po()
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    st = segs["ST"][0]
    assert st[1].strip() == "855"


def test_855_bak_accept_mode() -> None:
    """BAK02 must be AE for accept-as-is mode."""
    po = _make_po()
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    bak = segs["BAK"][0]
    assert bak[2].strip() == AckMode.ACCEPT_AS_IS.value  # "AE"


def test_855_bak_reject_mode() -> None:
    """BAK02 must be RD for reject mode."""
    po = _make_po(2)
    decisions = [
        LineAck(line_number=i + 1, sku=f"SKU-{i+1:03d}", original_qty=100, ack_code=LineAckCode.REJECT_LINE)
        for i in range(2)
    ]
    raw = from_po_with_changes(po, "VO-002", decisions, _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    bak = segs["BAK"][0]
    assert bak[2].strip() == AckMode.REJECT.value  # "RD"


def test_855_bak_change_mode() -> None:
    """BAK02 must be AT when at least one line differs."""
    po = _make_po(2)
    decisions = [
        LineAck(line_number=1, sku="SKU-001", original_qty=100, ack_code=LineAckCode.ACCEPT_AS_IS),
        LineAck(line_number=2, sku="SKU-002", original_qty=100, ack_code=LineAckCode.QUANTITY_CHANGE, accepted_qty=80),
    ]
    raw = from_po_with_changes(po, "VO-003", decisions, _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    bak = segs["BAK"][0]
    assert bak[2].strip() == AckMode.ACCEPT_WITH_CHANGES.value  # "AT"


def test_855_po_number_in_bak() -> None:
    """BAK03 must carry the original PO number."""
    po = _make_po()
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    bak = segs["BAK"][0]
    assert bak[3].strip() == "PO-TEST-001"


def test_855_line_count_in_ctt() -> None:
    """CTT01 must equal the number of lines acknowledged."""
    po = _make_po(5)
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    ctt = segs["CTT"][0]
    assert int(ctt[1].strip()) == 5


def test_855_po1_and_ack_segments_per_line() -> None:
    """Each line must produce exactly one PO1 and one ACK segment."""
    po = _make_po(3)
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    assert len(segs.get("PO1", [])) == 3
    assert len(segs.get("ACK", [])) == 3


def test_855_ack_ia_code_on_accept() -> None:
    """ACK01 must be IA (accept as-is) for auto-accept."""
    po = _make_po(1)
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    ack = segs["ACK"][0]
    assert ack[1].strip() == LineAckCode.ACCEPT_AS_IS.value  # "IA"


def test_855_ref_segment_vendor_order_number() -> None:
    """REF*VN must carry the vendor order number."""
    po = _make_po(1)
    raw = from_po_auto_accept(po, "VENDOR-ORD-99", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    assert "REF" in segs
    ref = segs["REF"][0]
    assert ref[1].strip() == "VN"
    assert ref[2].strip() == "VENDOR-ORD-99"


def test_855_se_segment_count_consistency() -> None:
    """SE01 (segment count) must equal the number of segments between ST and SE inclusive."""
    po = _make_po(2)
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    text = raw.decode("ascii")
    segment_sep = text[105]
    element_sep = text[3]
    all_segs = [s.strip() for s in text.split(segment_sep) if s.strip()]

    st_idx = next(i for i, s in enumerate(all_segs) if s.split(element_sep)[0].strip() == "ST")
    se_idx = next(i for i, s in enumerate(all_segs) if s.split(element_sep)[0].strip() == "SE")

    declared = int(all_segs[se_idx].split(element_sep)[1].strip())
    actual = se_idx - st_idx + 1  # ST through SE inclusive
    assert declared == actual, f"SE count {declared} != actual {actual}"


def test_855_dtm_ship_date_present() -> None:
    """DTM*002 segment must carry the requested ship date."""
    po = _make_po(1)
    raw = from_po_auto_accept(po, "VO-001", date(2026, 5, 1), _SENDER, _RECEIVER)
    segs = _parse_segments(raw)
    assert "DTM" in segs
    dtm = segs["DTM"][0]
    assert dtm[1].strip() == "002"
    assert dtm[2].strip() == "20260501"


def test_build_855_direct_api() -> None:
    """build_855 convenience function produces valid bytes."""
    ack = AckData(
        po_number="PO-DIRECT",
        po_date=date(2026, 4, 15),
        vendor_order_number="VO-DIRECT",
        mode=AckMode.ACCEPT_AS_IS,
        line_acks=[
            LineAck(line_number=1, sku="ABC", original_qty=50, ack_code=LineAckCode.ACCEPT_AS_IS)
        ],
    )
    raw = build_855(ack, _SENDER, _RECEIVER)
    assert b"ST*855" in raw
    assert b"BAK*00*AE*PO-DIRECT" in raw
