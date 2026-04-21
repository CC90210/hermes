"""
scripts/printer_tool.py
-----------------------
Windows printer control for Hermes.

Supports:
  - Listing installed printers
  - Showing the default printer
  - Printing PDF/document files via ShellExecute
  - Sending raw ZPL to thermal printers (Zebra)
  - Querying and cancelling print jobs

Requires pywin32 on Windows. Degrades gracefully on non-Windows platforms.

Usage:
    python scripts/printer_tool.py --list
    python scripts/printer_tool.py --default
    python scripts/printer_tool.py --print <file.pdf> [--printer NAME] [--copies N]
    python scripts/printer_tool.py --print-zpl <file.zpl> --printer <THERMAL>
    python scripts/printer_tool.py --print-zpl-string "^XA...^XZ" --printer <THERMAL>
    python scripts/printer_tool.py --status <job_id>
    python scripts/printer_tool.py --cancel <job_id>

Add --json to any command for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import asyncio
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional pywin32 import — graceful fallback on non-Windows
# ---------------------------------------------------------------------------

try:
    import win32api  # type: ignore[import]
    import win32print  # type: ignore[import]

    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False

_WIN32_MSG = (
    "Printer control requires Windows + pywin32. "
    "Install with: pip install pywin32"
)

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PrinterInfo:
    name: str
    driver: str
    port: str
    status: int
    is_default: bool


@dataclass
class PrintResult:
    success: bool
    job_id: int | None
    printer_name: str
    error: str | None


# ---------------------------------------------------------------------------
# Audit logging helper (non-blocking; import is optional)
# ---------------------------------------------------------------------------


def _audit(action: str, details: dict[str, Any]) -> None:
    """Best-effort audit log. Never raises."""
    try:
        db_path_str = os.environ.get("DB_PATH", "./storage/lowinger.db")
        db_path = Path(db_path_str)

        # Only attempt if the db module and database exist
        if not db_path.exists():
            return

        import asyncio as _asyncio

        from storage.db import log_audit as _log_audit

        async def _write() -> None:
            await _log_audit(db_path, agent_name="printer", action=action, details=details)

        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                # Schedule but don't wait — fire-and-forget
                loop.create_task(_write())
            else:
                loop.run_until_complete(_write())
        except RuntimeError:
            _asyncio.run(_write())
    except Exception:  # noqa: BLE001 — intentionally swallowed
        pass


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def list_printers() -> list[PrinterInfo]:
    """Return all locally visible printers.

    On non-Windows returns an empty list with a warning on stderr.
    """
    if not _WIN32_AVAILABLE:
        print(_WIN32_MSG, file=sys.stderr)
        return []

    default_name = ""
    try:
        default_name = win32print.GetDefaultPrinter()
    except Exception:  # noqa: BLE001
        pass

    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    raw = win32print.EnumPrinters(flags, None, 2)

    result: list[PrinterInfo] = []
    for entry in raw:
        name = entry.get("pPrinterName", "")
        result.append(
            PrinterInfo(
                name=name,
                driver=entry.get("pDriverName", ""),
                port=entry.get("pPortName", ""),
                status=entry.get("Status", 0),
                is_default=(name == default_name),
            )
        )
    return result


def default_printer() -> str | None:
    """Return the name of the system default printer, or None."""
    if not _WIN32_AVAILABLE:
        print(_WIN32_MSG, file=sys.stderr)
        return None
    try:
        return win32print.GetDefaultPrinter()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not retrieve default printer: {exc}", file=sys.stderr)
        return None


def print_pdf(path: str, printer: str | None = None, copies: int = 1) -> PrintResult:
    """Print a PDF (or any file) using the Windows Shell print verb.

    Uses 'printto' for a named printer, 'print' for the default printer.
    """
    if not _WIN32_AVAILABLE:
        return PrintResult(success=False, job_id=None, printer_name=printer or "", error=_WIN32_MSG)

    abs_path = str(Path(path).resolve())
    target_printer = printer or default_printer() or ""

    try:
        for _ in range(copies):
            if printer:
                win32api.ShellExecute(0, "printto", abs_path, f'"{printer}"', ".", 0)
            else:
                win32api.ShellExecute(0, "print", abs_path, None, ".", 0)

        # Brief wait for spooler to register the job
        time.sleep(1)

        _audit("print_pdf", {"file": abs_path, "printer": target_printer, "copies": copies})
        return PrintResult(success=True, job_id=None, printer_name=target_printer, error=None)
    except Exception as exc:  # noqa: BLE001
        _audit("print_pdf_error", {"file": abs_path, "printer": target_printer, "error": str(exc)})
        return PrintResult(success=False, job_id=None, printer_name=target_printer, error=str(exc))


def print_zpl_raw(zpl_bytes: bytes, printer_name: str) -> PrintResult:
    """Send raw ZPL bytes directly to a thermal printer using the RAW datatype.

    This bypasses the Windows GDI driver entirely — required for Zebra printers
    which speak ZPL natively and should never be rendered through a PDF driver.
    """
    if not _WIN32_AVAILABLE:
        return PrintResult(success=False, job_id=None, printer_name=printer_name, error=_WIN32_MSG)

    job_id: int | None = None
    try:
        h_printer = win32print.OpenPrinter(printer_name)
        try:
            job_id = win32print.StartDocPrinter(h_printer, 1, ("Hermes ZPL", None, "RAW"))
            try:
                win32print.StartPagePrinter(h_printer)
                win32print.WritePrinter(h_printer, zpl_bytes)
                win32print.EndPagePrinter(h_printer)
            finally:
                win32print.EndDocPrinter(h_printer)
        finally:
            win32print.ClosePrinter(h_printer)

        _audit("print_zpl", {"printer": printer_name, "bytes": len(zpl_bytes), "job_id": job_id})
        return PrintResult(success=True, job_id=job_id, printer_name=printer_name, error=None)
    except Exception as exc:  # noqa: BLE001
        _audit("print_zpl_error", {"printer": printer_name, "error": str(exc)})
        return PrintResult(success=False, job_id=job_id, printer_name=printer_name, error=str(exc))


def job_status(job_id: int, printer_name: str | None = None) -> dict[str, Any]:
    """Return a dict describing a spooler job's current state.

    If printer_name is omitted, searches all local printers for the job.
    """
    if not _WIN32_AVAILABLE:
        return {"error": _WIN32_MSG}

    printers_to_check: list[str] = []
    if printer_name:
        printers_to_check = [printer_name]
    else:
        printers_to_check = [p.name for p in list_printers()]

    for pname in printers_to_check:
        try:
            h = win32print.OpenPrinter(pname)
            try:
                info = win32print.GetJob(h, job_id, 1)
                return {
                    "job_id": job_id,
                    "printer": pname,
                    "document": info.get("pDocument", ""),
                    "status": info.get("Status", 0),
                    "pages_printed": info.get("PagesPrinted", 0),
                    "total_pages": info.get("TotalPages", 0),
                }
            except Exception:  # noqa: BLE001
                pass
            finally:
                win32print.ClosePrinter(h)
        except Exception:  # noqa: BLE001
            continue

    return {"error": f"Job {job_id} not found on any checked printer"}


def cancel_job(job_id: int, printer_name: str) -> PrintResult:
    """Cancel a queued or printing job by ID."""
    if not _WIN32_AVAILABLE:
        return PrintResult(success=False, job_id=job_id, printer_name=printer_name, error=_WIN32_MSG)

    try:
        h = win32print.OpenPrinter(printer_name)
        try:
            win32print.SetJob(h, job_id, 0, None, win32print.JOB_CONTROL_DELETE)
        finally:
            win32print.ClosePrinter(h)
        _audit("cancel_job", {"job_id": job_id, "printer": printer_name})
        return PrintResult(success=True, job_id=job_id, printer_name=printer_name, error=None)
    except Exception as exc:  # noqa: BLE001
        return PrintResult(success=False, job_id=job_id, printer_name=printer_name, error=str(exc))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _emit(data: Any, as_json: bool) -> None:
    if as_json:
        if hasattr(data, "__dataclass_fields__"):
            print(json.dumps(asdict(data)))
        elif isinstance(data, list):
            print(json.dumps([asdict(x) if hasattr(x, "__dataclass_fields__") else x for x in data]))
        else:
            print(json.dumps(data))
    else:
        if isinstance(data, list):
            for item in data:
                if hasattr(item, "__dataclass_fields__"):
                    d = asdict(item)
                    default_flag = " [DEFAULT]" if d.get("is_default") else ""
                    print(f"  {d['name']}{default_flag}  (port={d['port']}, driver={d['driver']})")
                else:
                    print(f"  {item}")
        elif hasattr(data, "__dataclass_fields__"):
            for k, v in asdict(data).items():
                print(f"  {k}: {v}")
        else:
            print(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes printer control — Windows thermal + document printing"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all installed printers")
    group.add_argument("--default", action="store_true", help="Show the default printer name")
    group.add_argument("--print", metavar="FILE", dest="print_file", help="Print a file")
    group.add_argument("--print-zpl", metavar="ZPL_FILE", dest="print_zpl_file", help="Send a .zpl file to a thermal printer")
    group.add_argument("--print-zpl-string", metavar="ZPL_STRING", dest="print_zpl_string", help="Send a ZPL string to a thermal printer")
    group.add_argument("--status", metavar="JOB_ID", type=int, help="Query a print job status")
    group.add_argument("--cancel", metavar="JOB_ID", type=int, help="Cancel a print job")

    parser.add_argument("--printer", help="Target printer name (defaults to system default)")
    parser.add_argument("--copies", type=int, default=1, help="Number of copies (PDF only)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")

    args = parser.parse_args()

    if args.list:
        printers = list_printers()
        if not printers and not _WIN32_AVAILABLE:
            if args.as_json:
                print(json.dumps({"warning": _WIN32_MSG, "printers": []}))
            return 0
        _emit(printers, args.as_json)
        return 0

    if args.default:
        name = default_printer()
        if args.as_json:
            print(json.dumps({"default_printer": name}))
        else:
            print(name or "(none)")
        return 0

    if args.print_file:
        result = print_pdf(args.print_file, printer=args.printer, copies=args.copies)
        _emit(result, args.as_json)
        return 0 if result.success else 1

    if args.print_zpl_file:
        if not args.printer:
            print("--printer is required for ZPL printing", file=sys.stderr)
            return 2
        zpl_bytes = Path(args.print_zpl_file).read_bytes()
        result = print_zpl_raw(zpl_bytes, args.printer)
        _emit(result, args.as_json)
        return 0 if result.success else 1

    if args.print_zpl_string:
        if not args.printer:
            print("--printer is required for ZPL printing", file=sys.stderr)
            return 2
        zpl_bytes = args.print_zpl_string.encode("utf-8")
        result = print_zpl_raw(zpl_bytes, args.printer)
        _emit(result, args.as_json)
        return 0 if result.success else 1

    if args.status is not None:
        info = job_status(args.status, printer_name=args.printer)
        _emit(info, args.as_json)
        return 0 if "error" not in info else 1

    if args.cancel is not None:
        if not args.printer:
            print("--printer is required to cancel a job", file=sys.stderr)
            return 2
        result = cancel_job(args.cancel, args.printer)
        _emit(result, args.as_json)
        return 0 if result.success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
