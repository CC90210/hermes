"""Tests for adapters/matrix_expander.py — apparel size-color matrix expander."""

from __future__ import annotations

import pytest

from adapters.matrix_expander import (
    ItemCrossReference,
    collapse_to_matrix,
    detect_matrix_format,
    expand_matrix,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_PIPE_MATRIX = """\
Color | XS | S | M | L | XL | XXL
Navy  | 0  | 12 | 24 | 36 | 24 | 12
Black | 0  | 12 | 24 | 36 | 24 | 12
Red   | 0  | 6  | 12 | 18 | 12 | 6
"""

_TAB_MATRIX = "Color\tXS\tS\tM\tL\tXL\tXXL\nNavy\t0\t12\t24\t36\t24\t12\nBlack\t0\t12\t24\t36\t24\t12\nRed\t0\t6\t12\t18\t12\t6\n"

_KV_MATRIX = """\
Navy: XS=0 S=12 M=24 L=36 XL=24 XXL=12
Black: XS=0 S=12 M=24 L=36 XL=24 XXL=12
Red: XS=0 S=6 M=12 L=18 XL=12 XXL=6
"""

_FLAT_TEXT = """\
PO Number: PO-2026-001
Item: LWG-1001  Qty: 144  Price: $4.25
Item: LWG-1002  Qty: 72   Price: $8.50
"""


def _make_xref(style: str, colors: list[str], sizes: list[str]) -> ItemCrossReference:
    """Build a cross-reference covering every color×size combination."""
    b2v: dict[str, str] = {}
    v2b: dict[str, str] = {}
    v2u: dict[str, str] = {}
    upc_seed = 100000000000
    for color in colors:
        for size in sizes:
            composite = f"{style}-{color}-{size}"
            vendor_sku = f"V-{style}-{color[:3].upper()}-{size}"
            upc = str(upc_seed)
            b2v[composite] = vendor_sku
            v2b[vendor_sku] = composite
            v2u[vendor_sku] = upc
            upc_seed += 1
    return ItemCrossReference(buyer_to_vendor=b2v, vendor_to_buyer=v2b, vendor_to_upc=v2u)


# ---------------------------------------------------------------------------
# detect_matrix_format
# ---------------------------------------------------------------------------

def test_detect_pipe_matrix() -> None:
    assert detect_matrix_format(_PIPE_MATRIX) is True


def test_detect_tab_matrix() -> None:
    assert detect_matrix_format(_TAB_MATRIX) is True


def test_detect_kv_matrix() -> None:
    assert detect_matrix_format(_KV_MATRIX) is True


def test_detect_flat_text_not_matrix() -> None:
    assert detect_matrix_format(_FLAT_TEXT) is False


def test_detect_empty_string() -> None:
    assert detect_matrix_format("") is False


# ---------------------------------------------------------------------------
# expand_matrix — 3×6 produces correct item count
# ---------------------------------------------------------------------------

def test_expand_3x6_matrix_item_count() -> None:
    """3 colors × 6 sizes but first column is XS=0 → 3 × 5 non-zero + 3 × 1 zero = 15 items."""
    items = expand_matrix(_PIPE_MATRIX, "BT-2210")
    # Navy: 5 non-zero, Black: 5 non-zero, Red: 5 non-zero
    assert len(items) == 15


def test_expand_matrix_skips_zero_qty_cells() -> None:
    """Cells with qty=0 must not produce a MatrixLineItem."""
    items = expand_matrix(_PIPE_MATRIX, "BT-2210")
    for item in items:
        assert item.quantity > 0


def test_expand_matrix_style_code_propagated() -> None:
    items = expand_matrix(_PIPE_MATRIX, "BT-2210")
    for item in items:
        assert item.style_code == "BT-2210"


def test_expand_matrix_color_and_size_set() -> None:
    items = expand_matrix(_PIPE_MATRIX, "BT-2210")
    colors = {i.color_code for i in items}
    sizes = {i.size_code for i in items}
    assert "Navy" in colors
    assert "Black" in colors
    assert "Red" in colors
    assert "M" in sizes
    assert "XL" in sizes


def test_expand_matrix_xref_resolves_sku() -> None:
    xref = _make_xref("BT-2210", ["Navy", "Black", "Red"], ["S", "M", "L", "XL", "XXL"])
    items = expand_matrix(_PIPE_MATRIX, "BT-2210", xref=xref)
    sku_items = [i for i in items if i.sku is not None]
    assert len(sku_items) > 0


def test_expand_matrix_xref_upc_populated() -> None:
    xref = _make_xref("BT-2210", ["Navy", "Black", "Red"], ["S", "M", "L", "XL", "XXL"])
    items = expand_matrix(_PIPE_MATRIX, "BT-2210", xref=xref)
    for item in items:
        if item.sku is not None:
            assert item.upc is not None


def test_expand_matrix_no_xref_sku_is_none() -> None:
    """When no xref is provided every item's sku stays None (no warning expected)."""
    items = expand_matrix(_PIPE_MATRIX, "BT-2210")
    for item in items:
        assert item.sku is None


def test_expand_matrix_partial_xref_emits_warning() -> None:
    """When xref is provided but missing a key, a UserWarning is emitted."""
    # Xref covers only Navy×S — every other combination will trigger the warning.
    partial_xref = ItemCrossReference(
        buyer_to_vendor={"BT-WARN-Navy-S": "V-BT-WARN-NAV-S"},
        vendor_to_buyer={"V-BT-WARN-NAV-S": "BT-WARN-Navy-S"},
        vendor_to_upc={"V-BT-WARN-NAV-S": "100000000001"},
    )
    with pytest.warns(UserWarning, match="no xref entry"):
        expand_matrix(_PIPE_MATRIX, "BT-WARN", xref=partial_xref)


def test_expand_kv_format() -> None:
    items = expand_matrix(_KV_MATRIX, "BT-2210")
    assert len(items) == 15  # same counts as pipe matrix


def test_expand_tab_format() -> None:
    items = expand_matrix(_TAB_MATRIX, "BT-2210")
    assert len(items) == 15


# ---------------------------------------------------------------------------
# collapse_to_matrix round-trip
# ---------------------------------------------------------------------------

def test_collapse_to_matrix_round_trip() -> None:
    xref = _make_xref("BT-2210", ["Navy", "Black"], ["S", "M", "L"])
    items = expand_matrix(_PIPE_MATRIX, "BT-2210", xref=xref)
    # Only Navy and Black have 3 non-zero sizes: S, M, L
    navy_black = [i for i in items if i.color_code in ("Navy", "Black") and i.size_code in ("S", "M", "L")]
    matrix_str = collapse_to_matrix(navy_black)
    assert "Navy" in matrix_str
    assert "Black" in matrix_str
    assert "M" in matrix_str


def test_collapse_empty_list() -> None:
    assert collapse_to_matrix([]) == ""
