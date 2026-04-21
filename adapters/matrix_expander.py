"""Apparel size-color matrix PO expander.

Implements Phase 5b — Apparel Matrix Parser (PRE-LAUNCH if apparel SKUs present).

Walgreens apparel POs do not arrive as flat line items. A single style line
contains a size-color matrix — e.g., 6 colors × 8 sizes = 48 distinct SKUs
collapsed into one block. A generic PO parser silently produces wrong order
entries that result in short-ship chargebacks.

Reference: docs/WHOLESALE_RESEARCH.md — Section 6 (Apparel-Specific Complexity).
"""

from __future__ import annotations

import csv
import logging
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from adapters.po_parser import LineItem

_log = logging.getLogger(__name__)

# Recognised apparel size tokens (ordered largest-first so "XXL" matches before "XL")
_SIZE_TOKENS: list[str] = [
    "XXXL", "XXL", "XL", "XS", "S", "M", "L",
    # Numeric women's / children's sizes
    "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20",
    # Numeric jeans-style (28–44)
    *[str(n) for n in range(28, 45)],
]

_SIZE_TOKEN_SET: frozenset[str] = frozenset(t.upper() for t in _SIZE_TOKENS)


@dataclass
class MatrixLineItem(LineItem):
    """Extends LineItem with apparel attributes."""
    style_code: str = ""
    color_code: str = ""
    size_code: str = ""
    season_code: str = ""


@dataclass
class ItemCrossReference:
    """Maps buyer's item code to vendor's SKU, and vice versa."""
    buyer_to_vendor: dict[str, str]
    vendor_to_buyer: dict[str, str]
    vendor_to_upc: dict[str, str]

    @classmethod
    def from_csv(cls, csv_path: Path) -> "ItemCrossReference":
        """Load from a CSV with columns: buyer_code, vendor_sku, upc"""
        buyer_to_vendor: dict[str, str] = {}
        vendor_to_buyer: dict[str, str] = {}
        vendor_to_upc: dict[str, str] = {}
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                bc = (row.get("buyer_code") or "").strip()
                vs = (row.get("vendor_sku") or "").strip()
                upc = (row.get("upc") or "").strip()
                if bc and vs:
                    buyer_to_vendor[bc] = vs
                    vendor_to_buyer[vs] = bc
                if vs and upc:
                    vendor_to_upc[vs] = upc
        return cls(
            buyer_to_vendor=buyer_to_vendor,
            vendor_to_buyer=vendor_to_buyer,
            vendor_to_upc=vendor_to_upc,
        )

    def resolve_sku(self, buyer_code: str) -> Optional[str]:
        return self.buyer_to_vendor.get(buyer_code)

    def upc_for(self, vendor_sku: str) -> Optional[str]:
        return self.vendor_to_upc.get(vendor_sku)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_matrix_format(text: str) -> bool:
    """Return True if the text appears to contain a size-color matrix.

    Checks for:
    - Multiple recognised size tokens appearing as column headers in a row
    - Numeric data cells in subsequent rows (quantities per size)
    - KV format: ``Color: XS=0 S=12 M=24``
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        tokens = _tokenise_line(line)
        size_hits = sum(1 for t in tokens if t.upper() in _SIZE_TOKEN_SET)
        if size_hits >= 2:
            return True
        # KV format: extract keys from ``KEY=VALUE`` pairs
        kv_keys = re.findall(r"(\w+)\s*=\s*\d+", line)
        if sum(1 for k in kv_keys if k.upper() in _SIZE_TOKEN_SET) >= 2:
            return True
    # Secondary heuristic: keyword in header
    header_re = re.compile(r"\b(qty\s*by\s*size|size\s*break|size\s*run|size\s*chart)\b", re.I)
    if header_re.search(text):
        return True
    return False


# ---------------------------------------------------------------------------
# Expansion
# ---------------------------------------------------------------------------

def expand_matrix(
    matrix_text: str,
    style_code: str,
    xref: Optional[ItemCrossReference] = None,
    default_unit_price: float = 0.0,
) -> list[MatrixLineItem]:
    """Parse a size-color matrix text block and return one MatrixLineItem per cell where qty > 0.

    Supported formats:
    1. Tab/pipe-separated grid
    2. CSV-ish (comma-separated)
    3. Line-per-color: ``Navy: XS=0 S=12 M=24 L=36 XL=24``
    """
    lines = [ln.strip() for ln in matrix_text.splitlines() if ln.strip()]
    if not lines:
        return []

    # Try line-per-color format first
    if _looks_like_key_value(lines):
        return _expand_kv_format(lines, style_code, xref, default_unit_price)

    # Detect delimiter for tabular formats
    header_line = _find_header_line(lines)
    if header_line is None:
        _log.warning("expand_matrix: no size header found in matrix text")
        return []

    delimiter = _detect_delimiter(lines[header_line])
    header_tokens = [t.strip() for t in lines[header_line].split(delimiter)]
    size_columns: list[tuple[int, str]] = []
    for col_idx, tok in enumerate(header_tokens):
        if tok.upper() in _SIZE_TOKEN_SET:
            size_columns.append((col_idx, tok.upper()))

    if not size_columns:
        return []

    results: list[MatrixLineItem] = []
    for line in lines[header_line + 1:]:
        cells = [c.strip() for c in line.split(delimiter)]
        if not cells:
            continue
        color = cells[0].strip()
        if not color or color.upper() in _SIZE_TOKEN_SET:
            continue
        for col_idx, size_code in size_columns:
            if col_idx >= len(cells):
                continue
            raw_qty = cells[col_idx].strip()
            qty = _safe_int(raw_qty)
            if qty <= 0:
                continue
            results.append(
                _make_item(style_code, color, size_code, qty, default_unit_price, xref)
            )

    return results


def collapse_to_matrix(items: list[MatrixLineItem]) -> str:
    """Inverse: given flat line items, produce a matrix for human display."""
    if not items:
        return ""

    colors: list[str] = []
    sizes: list[str] = []
    seen_colors: set[str] = set()
    seen_sizes: set[str] = set()
    for item in items:
        if item.color_code not in seen_colors:
            colors.append(item.color_code)
            seen_colors.add(item.color_code)
        if item.size_code not in seen_sizes:
            sizes.append(item.size_code)
            seen_sizes.add(item.size_code)

    grid: dict[tuple[str, str], int] = {
        (item.color_code, item.size_code): item.quantity for item in items
    }

    col_width = 6
    header = "Color".ljust(12) + "".join(s.rjust(col_width) for s in sizes)
    rows = [header]
    for color in colors:
        row = color.ljust(12)
        for size in sizes:
            qty = grid.get((color, size), 0)
            row += str(qty).rjust(col_width)
        rows.append(row)
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tokenise_line(line: str) -> list[str]:
    for sep in ("|", "\t", ","):
        if sep in line:
            return [t.strip() for t in line.split(sep)]
    return line.split()


def _detect_delimiter(line: str) -> str:
    for sep in ("|", "\t", ","):
        if sep in line:
            return sep
    return ","


def _find_header_line(lines: list[str]) -> Optional[int]:
    for i, line in enumerate(lines):
        tokens = _tokenise_line(line)
        if sum(1 for t in tokens if t.strip().upper() in _SIZE_TOKEN_SET) >= 2:
            return i
    return None


def _looks_like_key_value(lines: list[str]) -> bool:
    kv_re = re.compile(r"\w+\s*[:=]\s*\w+")
    for line in lines[:5]:
        if kv_re.search(line):
            # Ensure it also has size tokens
            if any(tok.upper() in _SIZE_TOKEN_SET for tok in re.split(r"[\s=:,]+", line)):
                return True
    return False


def _expand_kv_format(
    lines: list[str],
    style_code: str,
    xref: Optional[ItemCrossReference],
    default_unit_price: float,
) -> list[MatrixLineItem]:
    """Handle lines like: ``Navy: XS=0 S=12 M=24``"""
    results: list[MatrixLineItem] = []
    for line in lines:
        colon_pos = line.find(":")
        if colon_pos == -1:
            continue
        color = line[:colon_pos].strip()
        rest = line[colon_pos + 1:]
        pairs = re.findall(r"(\w+)\s*=\s*(\d+)", rest)
        for size_raw, qty_raw in pairs:
            size = size_raw.upper()
            if size not in _SIZE_TOKEN_SET:
                continue
            qty = int(qty_raw)
            if qty <= 0:
                continue
            results.append(_make_item(style_code, color, size, qty, default_unit_price, xref))
    return results


def _make_item(
    style_code: str,
    color: str,
    size_code: str,
    qty: int,
    unit_price: float,
    xref: Optional[ItemCrossReference],
) -> MatrixLineItem:
    composite = f"{style_code}-{color}-{size_code}"
    vendor_sku: Optional[str] = None
    upc: Optional[str] = None

    if xref is not None:
        vendor_sku = xref.resolve_sku(composite)
        if vendor_sku is None:
            # xref was supplied but has no entry for this composite key — likely a
            # missing cross-reference row; warn so the operator can fix the table.
            warnings.warn(
                f"matrix_expander: no xref entry for composite key {composite!r}; sku will be None",
                UserWarning,
                stacklevel=2,
            )
        else:
            upc = xref.upc_for(vendor_sku)

    return MatrixLineItem(
        sku=vendor_sku,
        description=f"{style_code} {color} {size_code}",
        quantity=qty,
        unit_price=unit_price,
        upc=upc,
        style_code=style_code,
        color_code=color,
        size_code=size_code,
    )


def _safe_int(value: str) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0
