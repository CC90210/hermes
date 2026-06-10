"""Hermes eval adapter — exercises the repo's REAL code paths in dry-run.

Hermes is a wholesale-PO automation agent: inbound purchase orders (PDF / Excel /
EDI X12 850 / email body) are parsed into structured POData, validated, then
pushed to the A2000 ERP. The LLM extraction step (Ollama / cloud) needs a live
model, but several load-bearing steps around it are PURE and deterministic.
This adapter wires those:

  po_extraction  → adapters.po_parser._extract_text_edi  (X12 850 segment parser:
                   pulls PO number, buyer name, SKUs, qty, price out of raw EDI
                   bytes — no network, no model) + _build_po_data (extracted-dict
                   → POData mapper). The real parser the inbound EDI path calls.
  validation     → adapters.po_parser.validate_po  (PO field validator — the same
                   gate the orchestrator runs before order entry). KNOWN-correct
                   answers, so the suite catches a regression in the rules.
  parser_routing → adapters.cloud_parser._route  (backend selector from the
                   HERMES_PO_PARSER env var — pure, deterministic). Locks the
                   ollama/anthropic/openai/auto routing + invalid-value fallback.
  mistakes       → mined from memory/MISTAKES.md → honest needs-model backlog.

Not a reimplementation — these are the exact functions the inbound pipeline
(main.py → orchestrator → POParser) calls. The only thing stubbed is the LLM
boundary, which is out of scope for a deterministic offline gate.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
import sys
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _meta(cd: Path) -> dict:
    m, f = {}, cd / "meta.yaml"
    if f.exists():
        for ln in f.read_text(encoding="utf-8").splitlines():
            if ":" in ln and not ln.strip().startswith("#"):
                k, _, v = ln.partition(":")
                m[k.strip()] = v.strip()
    return m


def _read_input(cd: Path) -> str:
    """First non-comment line of task.md (the directive/input)."""
    task = (cd / "task.md").read_text(encoding="utf-8")
    for ln in task.splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            return s
    return ""


# --------------------------------------------------------------------------
# po_extraction — real X12 850 EDI parser + POData builder, fully offline
# --------------------------------------------------------------------------

def _po_extraction(cd: Path) -> dict:
    from adapters.po_parser import _extract_text_edi, _build_po_data

    # The case's EDI document lives in fixtures/po.edi
    edi_path = cd / "fixtures" / "po.edi"
    raw = edi_path.read_bytes()
    text = _extract_text_edi(raw)

    # Parse the human-readable summary the EDI extractor emits into structured
    # fields so the scorer can assert on individual values.
    po_number = None
    order_date = None
    buyer = None
    skus: list[str] = []
    qtys: list[int] = []
    for ln in text.splitlines():
        if ln.startswith("PO Number:"):
            po_number = ln.split(":", 1)[1].strip() or None
        elif ln.startswith("Order Date:"):
            order_date = ln.split(":", 1)[1].strip() or None
        elif ln.startswith("Bill-To Name:") or ln.startswith("Buyer Name:"):
            if buyer is None:
                buyer = ln.split(":", 1)[1].strip() or None
        elif ln.startswith("Line Item:"):
            m_sku = re.search(r"SKU=(\S+)", ln)
            m_qty = re.search(r"Qty=(\d+)", ln)
            if m_sku and m_sku.group(1):
                skus.append(m_sku.group(1))
            if m_qty:
                qtys.append(int(m_qty.group(1)))

    return {
        "raw_text": text,
        "po_number": po_number,
        "order_date": order_date,
        "buyer_name": buyer,
        "skus": skus,
        "line_count": len(skus),
        "quantities": qtys,
    }


# --------------------------------------------------------------------------
# validation — real validate_po gate; KNOWN-correct verdicts
# --------------------------------------------------------------------------

def _validation(cd: Path) -> dict:
    from adapters.po_parser import POData, LineItem, validate_po

    scenario = _read_input(cd)

    def _po(**over):
        base = dict(
            po_number="PO-2026-04567",
            customer_name="Walgreens #04231",
            customer_email="purchasing@walgreens.com",
            customer_address=None,
            ship_to_address=None,
            order_date=None,
            ship_date=None,
            line_items=[LineItem(sku="LWG-1001", description="Premium Cotton T-Shirt", quantity=144, unit_price=4.25)],
        )
        base.update(over)
        return POData(**base)

    builders = {
        "valid": lambda: _po(),
        "missing_po_number": lambda: _po(po_number=None),
        "blank_po_number": lambda: _po(po_number="   "),
        "missing_customer": lambda: _po(customer_name=None),
        "no_line_items": lambda: _po(line_items=[]),
        "zero_quantity": lambda: _po(line_items=[LineItem(sku="X", description="Test", quantity=0, unit_price=1.0)]),
        "blank_description": lambda: _po(line_items=[LineItem(sku="X", description="  ", quantity=5, unit_price=1.0)]),
    }
    build = builders.get(scenario)
    if build is None:
        raise NotImplementedError(f"unknown validation scenario {scenario!r}")

    errors = validate_po(build())
    low = " ".join(errors).lower()
    return {
        "scenario": scenario,
        "errors": errors,
        "error_count": len(errors),
        "is_valid": len(errors) == 0,
        "flags_po_number": "po number" in low,
        "flags_customer": "customer name" in low,
        "flags_line_items": "line item" in low,
        "flags_quantity": "quantity" in low,
        "flags_description": "description" in low,
    }


# --------------------------------------------------------------------------
# parser_routing — real _route backend selector; deterministic, no network
# --------------------------------------------------------------------------

def _parser_routing(cd: Path) -> dict:
    from adapters import cloud_parser

    value = _read_input(cd)
    # "<none>" means the env var is unset; otherwise set it to the literal.
    prev = os.environ.get("HERMES_PO_PARSER")
    try:
        if value == "<none>":
            os.environ.pop("HERMES_PO_PARSER", None)
        else:
            os.environ["HERMES_PO_PARSER"] = value
        route = cloud_parser._route()
    finally:
        if prev is None:
            os.environ.pop("HERMES_PO_PARSER", None)
        else:
            os.environ["HERMES_PO_PARSER"] = prev
    return {"input": value, "route": route}


# --------------------------------------------------------------------------
# mistakes — mined from memory/MISTAKES.md (honest needs-model backlog)
# --------------------------------------------------------------------------

def _mistakes(_cd: Path) -> dict:
    # Each mined mistake is a regression target. Until wired to a deterministic
    # check that would have caught it, it scores rubric -> needs-model (honest
    # pending, never a fake pass). Wiring each is the ongoing capability work.
    return {"verdict": "needs-model"}


DISPATCH = {
    "po_extraction": _po_extraction,
    "validation": _validation,
    "parser_routing": _parser_routing,
    "mistakes": _mistakes,
}


def run_case(case_dir) -> dict:
    cd = Path(case_dir)
    suite = _meta(cd).get("suite") or cd.parent.name
    fn = DISPATCH.get(suite)
    if fn is None:
        raise NotImplementedError(f"no adapter wired for suite {suite!r}")
    return fn(cd)
