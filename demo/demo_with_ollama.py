"""
demo/demo_with_ollama.py
------------------------
Full pipeline demo that uses the real Ollama LLM for PO extraction.

Requires:
    - Ollama running locally (default: http://localhost:11434)
    - Model pulled: ollama pull qwen2.5:32b  (or set OLLAMA_MODEL)

Usage:
    python -m demo.demo_with_ollama
    OLLAMA_MODEL=llama3.2 python -m demo.demo_with_ollama

Step timings are printed so you can demonstrate the end-to-end latency
to Emmanuel: "PO parsed in 2.3 seconds, full pipeline in 8.1 seconds."
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Rich terminal output — graceful fallback if not installed
# ---------------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    _RICH = True
except ImportError:
    console = None  # type: ignore[assignment]
    _RICH = False


def _step(icon: str, label: str, elapsed: float, detail: str = "") -> None:
    timing = f"[{elapsed:.2f}s]"
    if _RICH and console:
        from rich import print as rprint
        rprint(f"  {icon}  [bold green]{label}[/bold green]  [dim]{detail} {timing}[/dim]")
    else:
        print(f"  {icon}  {label}  {detail} {timing}")


def _banner(model: str, ollama_host: str) -> None:
    if _RICH and console:
        console.print(
            Panel(
                f"[bold]Real Ollama pipeline — step timings included[/bold]\n\n"
                f"  Model : [cyan]{model}[/cyan]\n"
                f"  Host  : [cyan]{ollama_host}[/cyan]\n"
                f"  A2000 : [cyan]Mock (in-memory)[/cyan]\n"
                f"  Email : [cyan]Simulated (not sent)[/cyan]",
                title="[bold yellow]Hermes — Ollama Demo[/bold yellow]",
                border_style="yellow",
            )
        )
    else:
        print("\nHermes — Ollama Demo")
        print(f"  Model: {model} | Host: {ollama_host}")
        print("  A2000: Mock | Email: Simulated")


# ---------------------------------------------------------------------------
# Check Ollama reachability before starting
# ---------------------------------------------------------------------------

def _check_ollama(host: str, model: str) -> None:
    import httpx

    try:
        resp = httpx.get(f"{host}/api/tags", timeout=5.0)
        resp.raise_for_status()
        tags = resp.json()
        models_available = [m["name"] for m in tags.get("models", [])]
        # Accept prefix match (e.g. "qwen2.5:32b" matches "qwen2.5:32b-instruct-q4_K_M")
        model_base = model.split(":")[0]
        if not any(model_base in m for m in models_available):
            print(f"\n  WARNING: model '{model}' not found in Ollama.")
            print(f"  Available: {models_available}")
            print(f"  Run: ollama pull {model}\n")
    except Exception as exc:
        print(f"\n  ERROR: Cannot reach Ollama at {host}: {exc}")
        print("  Make sure Ollama is running: ollama serve\n")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_demo_with_ollama() -> None:
    os.environ.setdefault("A2000_MODE", "mock")
    os.environ.setdefault("EMAIL_USER", "demo@lowinger.com")
    os.environ.setdefault("EMAIL_PASSWORD", "demo-password")

    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5:32b")
    _banner(ollama_model, ollama_host)
    print()

    _check_ollama(ollama_host, ollama_model)

    timings: dict[str, float] = {}
    pipeline_start = time.perf_counter()

    # -----------------------------------------------------------------------
    # Step 1: Read PO fixture
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_po.txt"
    if not fixture_path.exists():
        print(f"  ERROR: fixture not found at {fixture_path}")
        sys.exit(1)

    raw_text = fixture_path.read_text(encoding="utf-8")
    timings["read"] = time.perf_counter() - t0
    _step("📧", "PO received from inbox", timings["read"], f"({len(raw_text)} chars)")

    # -----------------------------------------------------------------------
    # Step 2: Parse with real Ollama
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    from adapters.po_parser import parse_po, validate_po

    print("  🤖  Sending to Ollama for extraction (may take 3-30s depending on model)...")
    po = parse_po(raw_text.encode(), "sample_po.txt", "text/plain")
    timings["parse"] = time.perf_counter() - t0
    _step("🤖", "PO parsed by Ollama", timings["parse"], f"(PO# {po.po_number}, {len(po.line_items)} lines)")

    errors = validate_po(po)
    if errors:
        print(f"  ERROR: validation failed: {'; '.join(errors)}")
        sys.exit(1)

    # Print extracted line items
    if _RICH and console:
        table = Table(title="Extracted Line Items", border_style="dim")
        table.add_column("SKU", style="cyan")
        table.add_column("Description")
        table.add_column("Qty", justify="right")
        table.add_column("Unit Price", justify="right")
        table.add_column("Line Total", justify="right")
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
        for item in po.line_items:
            print(f"    {item.sku or '?':12s}  {item.description:40s}  qty={item.quantity}")

    # -----------------------------------------------------------------------
    # Step 3: Enter into A2000 mock
    # -----------------------------------------------------------------------
    t0 = time.perf_counter()
    from adapters.a2000_client import MockA2000Client
    a2000 = MockA2000Client()
    result = await a2000.create_order(po)
    timings["enter"] = time.perf_counter() - t0

    if not result.success:
        print(f"  ERROR: A2000 entry failed: {result.message}")
        sys.exit(1)

    _step("📦", "Order entered into A2000", timings["enter"],
          f"(order_id={result.order_id}, invoice={result.invoice_number})")

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
    timings["invoice"] = time.perf_counter() - t0
    _step("🧾", "Invoice retrieved", timings["invoice"],
          f"({len(invoice_pkg.invoice_pdf)} bytes, invoice# {invoice_pkg.invoice_number})")

    # -----------------------------------------------------------------------
    # Step 5: Simulate email send
    # -----------------------------------------------------------------------
    _step("✉️", "Invoice would be emailed", 0.0,
          f"(to: {invoice_pkg.customer_email})")

    # -----------------------------------------------------------------------
    # Timing summary
    # -----------------------------------------------------------------------
    total = time.perf_counter() - pipeline_start
    print()

    if _RICH and console:
        timing_table = Table(title="Step Timings", border_style="dim")
        timing_table.add_column("Step")
        timing_table.add_column("Time", justify="right", style="cyan")
        timing_table.add_row("Read PO from disk", f"{timings['read']:.3f}s")
        timing_table.add_row("Parse PO (Ollama)", f"{timings['parse']:.3f}s")
        timing_table.add_row("Enter into A2000 (mock)", f"{timings['enter']:.3f}s")
        timing_table.add_row("Retrieve invoice", f"{timings['invoice']:.3f}s")
        timing_table.add_row("[bold]Total end-to-end[/bold]", f"[bold]{total:.3f}s[/bold]")
        console.print(timing_table)

        console.print(
            Panel(
                f"[bold green]Pipeline complete![/bold green]\n\n"
                f"  PO# {po.po_number} | Customer: {po.customer_name}\n"
                f"  Invoice {invoice_pkg.invoice_number} ready for {invoice_pkg.customer_email}\n"
                f"  Ollama parse: {timings['parse']:.2f}s — total: {total:.2f}s",
                title="[bold green]Success[/bold green]",
                border_style="green",
            )
        )
    else:
        print("  Timing breakdown:")
        print(f"    Read PO:        {timings['read']:.3f}s")
        print(f"    Ollama parse:   {timings['parse']:.3f}s")
        print(f"    A2000 entry:    {timings['enter']:.3f}s")
        print(f"    Invoice fetch:  {timings['invoice']:.3f}s")
        print(f"    TOTAL:          {total:.3f}s")
        print()
        print(f"  PO# {po.po_number} | Invoice {invoice_pkg.invoice_number}")
        print(f"  Ollama extracted {len(po.line_items)} line items in {timings['parse']:.2f}s")


def main() -> None:
    asyncio.run(run_demo_with_ollama())


if __name__ == "__main__":
    main()
