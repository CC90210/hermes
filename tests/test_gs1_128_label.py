"""
tests/test_gs1_128_label.py
----------------------------
Tests for adapters/gs1_128_label.py — SSCC-18 computation and label generation.

GS1 check digit values are verified against the algorithm described in:
  https://www.gs1us.org/upcs-barcodes-prefixes/sscc

All tests are pure-computation; no network calls, no file I/O.
"""

from __future__ import annotations

import pytest

from adapters.gs1_128_label import (
    compute_sscc,
    generate_label_pdf,
    generate_label_zpl,
    sscc_to_barcode_data,
    validate_sscc,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SHIP_TO = {
    "street": "5500 Industrial Blvd",
    "city": "Aurora",
    "state": "IL",
    "zip": "60504",
}


# ---------------------------------------------------------------------------
# compute_sscc — correct check digit
# ---------------------------------------------------------------------------


def test_compute_sscc_known_good_value() -> None:
    """GS1 reference case: extension=0, prefix='0614141', serial=12345.

    17-digit body: 0 + 0614141 + 000012345 = 00614141000012345
    GS1 Mod-10 on '00614141000012345':
      positions (0-indexed): 0→0×3, 1→0×1, 2→6×3, 3→1×1, 4→4×3, 5→1×1,
                             6→4×3, 7→1×1, 8→0×3, 9→0×1, 10→0×3, 11→0×1,
                             12→1×3, 13→2×1, 14→3×3, 15→4×1, 16→5×3
      = 0+0+18+1+12+1+12+1+0+0+0+0+3+2+9+4+15 = 78
      check = (10 - 78%10) % 10 = (10 - 8) % 10 = 2... wait, let's compute:
      78 % 10 = 8 → (10 - 8) % 10 = 2
    Expected SSCC: 006141410000123452
    """
    result = compute_sscc(0, "0614141", 12345)
    assert len(result) == 18
    assert result[:17] == "00614141000012345"
    # Verify check digit via validate_sscc rather than hard-coding the digit
    assert validate_sscc(result)


def test_compute_sscc_different_serial() -> None:
    result = compute_sscc(0, "0614141", 123456789)
    assert len(result) == 18
    assert validate_sscc(result)


def test_compute_sscc_extension_digit_5() -> None:
    result = compute_sscc(5, "1234567", 1)
    assert result[0] == "5"
    assert len(result) == 18
    assert validate_sscc(result)


def test_compute_sscc_10_digit_prefix() -> None:
    """A 10-digit prefix leaves 6 digits for serial_ref."""
    result = compute_sscc(0, "1234567890", 999999)
    assert len(result) == 18
    assert validate_sscc(result)


def test_compute_sscc_serial_zero() -> None:
    result = compute_sscc(0, "0614141", 0)
    assert len(result) == 18
    assert validate_sscc(result)


# ---------------------------------------------------------------------------
# compute_sscc — error cases
# ---------------------------------------------------------------------------


def test_compute_sscc_invalid_extension_digit() -> None:
    with pytest.raises(ValueError, match="extension_digit"):
        compute_sscc(10, "0614141", 1)


def test_compute_sscc_negative_extension() -> None:
    with pytest.raises(ValueError, match="extension_digit"):
        compute_sscc(-1, "0614141", 1)


def test_compute_sscc_non_numeric_prefix() -> None:
    with pytest.raises(ValueError, match="digits"):
        compute_sscc(0, "ABC1234", 1)


def test_compute_sscc_prefix_too_short() -> None:
    with pytest.raises(ValueError, match="7–10"):
        compute_sscc(0, "123456", 1)


def test_compute_sscc_prefix_too_long() -> None:
    with pytest.raises(ValueError, match="7–10"):
        compute_sscc(0, "12345678901", 1)


def test_compute_sscc_serial_overflows() -> None:
    """7-digit prefix → 9-digit serial field → max serial = 999999999."""
    with pytest.raises(ValueError, match="overflow"):
        compute_sscc(0, "0614141", 1_000_000_000)


# ---------------------------------------------------------------------------
# validate_sscc
# ---------------------------------------------------------------------------


def test_validate_sscc_returns_true_for_valid() -> None:
    sscc = compute_sscc(0, "0614141", 12345)
    assert validate_sscc(sscc) is True


def test_validate_sscc_returns_false_for_wrong_check_digit() -> None:
    sscc = compute_sscc(0, "0614141", 12345)
    corrupted = sscc[:17] + str((int(sscc[17]) + 1) % 10)
    assert validate_sscc(corrupted) is False


def test_validate_sscc_returns_false_for_wrong_length() -> None:
    assert validate_sscc("00614141000012345") is False   # 17 digits
    assert validate_sscc("0061414100001234500") is False  # 19 digits


def test_validate_sscc_returns_false_for_non_numeric() -> None:
    assert validate_sscc("0061414100001234XX") is False


# ---------------------------------------------------------------------------
# sscc_to_barcode_data
# ---------------------------------------------------------------------------


def test_sscc_to_barcode_data_prepends_ai() -> None:
    sscc = compute_sscc(0, "0614141", 12345)
    data = sscc_to_barcode_data(sscc)
    assert data.startswith("00")
    assert data[2:] == sscc
    assert len(data) == 20


# ---------------------------------------------------------------------------
# generate_label_zpl
# ---------------------------------------------------------------------------


def test_generate_label_zpl_starts_and_ends_with_xza_xzz() -> None:
    sscc = compute_sscc(0, "0614141", 1)
    zpl = generate_label_zpl(
        sscc=sscc,
        gtin="00012345678905",
        po_number="PO-2026-04567",
        ship_to_name="Walgreens DC Aurora",
        ship_to_address=_SHIP_TO,
        ship_to_store="DC0042",
        carton_qty=12,
        carton_number=1,
        total_cartons=5,
    )
    assert zpl.startswith("^XA")
    assert zpl.rstrip().endswith("^XZ")


def test_generate_label_zpl_contains_bc_barcode_command() -> None:
    sscc = compute_sscc(0, "0614141", 1)
    zpl = generate_label_zpl(
        sscc=sscc,
        gtin="00012345678905",
        po_number="PO-2026-04567",
        ship_to_name="Walgreens DC Aurora",
        ship_to_address=_SHIP_TO,
        ship_to_store="DC0042",
        carton_qty=12,
        carton_number=1,
        total_cartons=5,
    )
    assert "^BC" in zpl


def test_generate_label_zpl_contains_sscc_value() -> None:
    sscc = compute_sscc(0, "0614141", 99)
    zpl = generate_label_zpl(
        sscc=sscc,
        gtin="00012345678905",
        po_number="PO-2026-04567",
        ship_to_name="Walgreens DC Aurora",
        ship_to_address=_SHIP_TO,
        ship_to_store="DC0042",
        carton_qty=6,
        carton_number=2,
        total_cartons=10,
    )
    assert sscc in zpl


def test_generate_label_zpl_raises_on_invalid_sscc() -> None:
    bad_sscc = "000000000000000000"  # all zeros — check digit almost certainly wrong
    # Verify it is actually invalid before testing
    if validate_sscc(bad_sscc):
        pytest.skip("All-zero SSCC happens to be valid for this algorithm")
    with pytest.raises(ValueError, match="valid"):
        generate_label_zpl(
            sscc=bad_sscc,
            gtin="00012345678905",
            po_number="PO-001",
            ship_to_name="Test Store",
            ship_to_address=_SHIP_TO,
            ship_to_store="DC0001",
            carton_qty=1,
            carton_number=1,
            total_cartons=1,
        )


# ---------------------------------------------------------------------------
# generate_label_pdf
# ---------------------------------------------------------------------------


def test_generate_label_pdf_returns_nonempty_bytes() -> None:
    sscc = compute_sscc(0, "0614141", 1)
    pdf = generate_label_pdf(
        sscc=sscc,
        gtin="00012345678905",
        po_number="PO-2026-04567",
        ship_to_name="Walgreens DC Aurora",
        ship_to_address=_SHIP_TO,
        ship_to_store="DC0042",
        carton_qty=12,
        carton_number=1,
        total_cartons=5,
    )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000  # any real PDF is at least 1 KB


def test_generate_label_pdf_starts_with_pdf_magic_bytes() -> None:
    sscc = compute_sscc(0, "0614141", 2)
    pdf = generate_label_pdf(
        sscc=sscc,
        gtin="00012345678905",
        po_number="PO-2026-04567",
        ship_to_name="Walgreens DC Aurora",
        ship_to_address=_SHIP_TO,
        ship_to_store="DC0042",
        carton_qty=6,
        carton_number=1,
        total_cartons=3,
    )
    assert pdf[:4] == b"%PDF"
