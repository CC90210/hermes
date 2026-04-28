"""
demo/run_demo.py
----------------
End-to-end demo for Emmanuel — no Outlook credentials required.

Pipeline:
    Read PO file -> Parse PO (mock or Ollama) -> Enter into A2000 (mock)
    -> Retrieve invoice -> Show what would be emailed

Usage:
    python -m demo.run_demo                    # uses mock PO extractor
    USE_OLLAMA=1 python -m demo.run_demo       # uses real Ollama (must be running)

Runtime: < 30 seconds. No real POS, no real email, no real Ollama needed.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Force UTF-8 stdout/stderr on Windows so emoji and box-drawing characters
# render instead of crashing the legacy cp1252 console. This must run before
# any print or Rich import.
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ---------------------------------------------------------------------------
# Rich terminal output — graceful fallback if not installed
# ---------------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint

    console = Console()
    _RICH = True
except ImportError:
    console = None  # type: ignore[assignment]
    _RICH = False

    def rprint(*args: object, **kwargs: object) -> None:  # type: ignore[misc]
        print(*args)


def _header(text: str) -> None:
    if _RICH and console:
        console.rule(f"[bold cyan]{text}[/bold cyan]")
    else:
        print(f"\n{'=' * 60}")
        print(f"  {text}")
        print("=" * 60)


def _step(icon: str, label: str, detail: str = "") -> None:
    if _RICH:
        rprint(f"  {icon}  [bold green]{label}[/bold green]  [dim]{detail}[/dim]")
    else:
        print(f"  {icon}  {label}  {detail}")


def _error(msg: str) -> None:
    if _RICH:
        rprint(f"  [bold red]ERROR:[/bold red] {msg}")
    else:
        print(f"  ERROR: {msg}")


# ---------------------------------------------------------------------------
# Mock PO extraction (no Ollama required)
# ---------------------------------------------------------------------------

def _mock_extract_po(raw_text: str):  # type: ignore[return]
    """Return a realistic POData directly from the fixture text — no LLM call."""
    # Import here so env vars set below are picked up
    from adapters.po_parser import LineItem, POData

    return POData(
        po_number="PO-2026-04567",
        customer_name="Walgreens #04231",
        customer_email="purchasing@walgreens.com",
        customer_address="1234 Market Street, Chicago, IL 60601",
        ship_to_address="5500 Industrial Blvd, Aurora, IL 60504",
        order_date="2026-04-15",
        ship_date="2026-04-22",
        notes="Please ship via standard freight. Confirm receipt by EOD 2026-04-16.",
        line_items=[
            LineItem(
                sku="LWG-1001",
                description="Premium Cotton T-Shirt - Black M",
                quantity=144,
                unit_price=4.25,
            ),
            LineItem(
                sku="LWG-1002",
                description="Premium Cotton T-Shirt - Black L",
                quantity=144,
                unit_price=4.25,
            ),
            LineItem(
                sku="LWG-2050",
                description="Athletic Sock 6-Pack White",
                quantity=72,
                unit_price=8.50,
            ),
        ],
        raw_text=raw_text,
    )


# ---------------------------------------------------------------------------
# Demo pipeline
# ---------------------------------------------------------------------------

async def run_demo() -> None:
    # Force mock mode — no real A2000 or email
    os.environ.setdefault("A2000_MODE", "mock")
    os.environ.setdefault("EMAIL_USER", "demo@lowinger.com")
    os.environ.setdefault("EMAIL_PASSWORD", "demo-password")

    use_ollama = os.environ.get("USE_OLLAMA", "").strip() in ("1", "true", "yes")

    _header("Hermes — Live Demo")

    if _RICH and console:
        console.print(
            Panel(
                "[bold]This demo shows the full automated order workflow[/bold]\n"
                "without requiring Outlook, A2000, or a live Ollama instance.\n\n"
                f"Mode: [cyan]{'Real Ollama' if use_ollama else 'Mock extractor (instant)'}[/cyan]  |  "
                "A2000: [cyan]Mock (in-memory)[/cyan]  |  "
                "Email: [cyan]Simulated (not sent)[/cyan]",
                title="[bold yellow]Hermes — The Commerce Agent[/bold yellow]",
                border_style="yellow",
            )
        )
    else:
        print("\nHermes — automated order processing demo")
        print(f"Mode: {'Real Ollama' if use_ollama else 'Mock extractor'} | A2000: Mock | Email: Simulated")

    print()
    demo_start = time.perf_counter()

    # -----------------------------------------------------------------------
    # Step 1: Read PO file
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_po.txt"

    if not fixture_path.exists():
        _error(f"Fixture not found: {fixture_path}")
        sys.exit(1)

    raw_text = fixture_path.read_text(encoding="utf-8")
    t1 = time.perf_counter()
    _step("📧", "PO received", f"({fixture_path.name}, {len(raw_text)} chars) [{t1 - t0:.2f}s]")

    # -----------------------------------------------------------------------
    # Step 2: Parse PO
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    if use_ollama:
        from adapters.po_parser import parse_po
        po = parse_po(raw_text.encode(), "sample_po.txt", "text/plain")
    else:
        po = _mock_extract_po(raw_text)
    t1 = time.perf_counter()
    _step("🤖", "PO parsed", f"(PO# {po.po_number}, {len(po.line_items)} line items) [{t1 - t0:.2f}s]")

    from adapters.po_parser import validate_po
    errors = validate_po(po)
    if errors:
        _error("Validation failed: " + "; ".join(errors))
        sys.exit(1)

    # Print line item table
    if _RICH and console:
        table = Table(title="Purchase Order Details", border_style="dim")
        table.add_column("SKU", style="cyan")
        table.add_column("Description")
        table.add_column("Qty", justify="right")
        table.add_column("Unit Price", justify="right")
        table.add_column("Total", justify="right")
        for item in po.line_items:
            total = item.quantity * item.unit_price
            table.add_row(
                item.sku or "—",
                item.description,
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${total:.2f}",
            )
        console.print(table)
    else:
        print(f"\n  Customer : {po.customer_name}")
        print(f"  Email    : {po.customer_email}")
        print(f"  Ship By  : {po.ship_date}")
        for item in po.line_items:
            print(f"    {item.sku:12s}  {item.description:40s}  qty={item.quantity}  @${item.unit_price:.2f}")
        print()

    # -----------------------------------------------------------------------
    # Step 3: Enter into A2000 (mock)
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    from adapters.a2000_client import MockA2000Client
    a2000 = MockA2000Client()
    result = await a2000.create_order(po)
    t1 = time.perf_counter()

    if not result.success:
        _error(f"A2000 entry failed: {result.message}")
        sys.exit(1)

    _step(
        "📦",
        "Order entered into A2000",
        f"(order_id={result.order_id}, invoice={result.invoice_number}) [{t1 - t0:.2f}s]",
    )

    # -----------------------------------------------------------------------
    # Step 4: Retrieve invoice
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    from adapters.invoice_generator import get_invoice_for_order
    invoice_pkg = await get_invoice_for_order(
        result.order_id,
        a2000,
        customer_name=po.customer_name,
        customer_email=po.customer_email,
        po_number=po.po_number,
        invoice_number=result.invoice_number,
    )
    t1 = time.perf_counter()
    _step(
        "🧾",
        "Invoice retrieved",
        f"({len(invoice_pkg.invoice_pdf)} bytes, invoice# {invoice_pkg.invoice_number}) [{t1 - t0:.2f}s]",
    )

    # -----------------------------------------------------------------------
    # Step 5: Show what would be emailed (no actual send)
    # -----------------------------------------------------------------------
    _step(
        "✉️",
        "Invoice would be emailed",
        f"(to: {invoice_pkg.customer_email}, subject: {invoice_pkg.subject_line})",
    )

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    total_elapsed = time.perf_counter() - demo_start
    print()
    if _RICH and console:
        console.print(
            Panel(
                f"[bold green]All 5 pipeline steps completed successfully![/bold green]\n\n"
                f"  PO#     : [cyan]{po.po_number}[/cyan]\n"
                f"  Customer: [cyan]{po.customer_name}[/cyan]\n"
                f"  Email   : [cyan]{invoice_pkg.customer_email}[/cyan]\n"
                f"  Invoice : [cyan]{invoice_pkg.invoice_number}[/cyan]\n"
                f"  Runtime : [bold]{total_elapsed:.2f}s[/bold]",
                title="[bold green]Demo Complete[/bold green]",
                border_style="green",
            )
        )
    else:
        print("  Demo complete!")
        print(f"  PO# {po.po_number} | Invoice {invoice_pkg.invoice_number}")
        print(f"  Total runtime: {total_elapsed:.2f}s")
        print()


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
