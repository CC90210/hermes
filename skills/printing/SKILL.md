---
name: printing
description: How Hermes handles physical printing — warehouse POs, GS1-128 carton labels, invoices
tags: [hermes, skills, printing, phase-2c]
---

# SKILL — Printing

> How Hermes controls printers. Windows-first, graceful degradation on non-Windows.

## When to Print

| Document | Trigger | Printer | Env Gate |
|----------|---------|---------|----------|
| Warehouse PO | Every successful A2000 order entry (Step 3) | `WAREHOUSE_PRINTER_NAME` | `HERMES_PRINT_WAREHOUSE_PO=1` |
| GS1-128 carton label | Every shipment (called from label workflow) | `LABEL_PRINTER_NAME` | `HERMES_PRINT_LABELS=1` |
| Invoice | On explicit request only ("print me the invoice for order 42") | `WAREHOUSE_PRINTER_NAME` | Manual |

Printing is **always opt-in**. Default for all flags is `0` (disabled).

## Finding Printer Names

The exact Windows printer name must match what the OS reports:

```bash
python scripts/printer_tool.py --list
```

Copy the `name` field verbatim into `WAREHOUSE_PRINTER_NAME` or `LABEL_PRINTER_NAME` in `.env`.

Common names:
- `HP LaserJet Pro MFP M428fdw (1)` — typical office laser
- `ZDesigner ZT411-300dpi ZPL` — Zebra label printer (exact model string varies)

## Printer Types

**Standard printer (warehouse PO, invoice):** Any PCL/PDF-capable printer. Hermes generates
a PDF and sends it via the Windows Shell `printto` verb. The driver renders it.

**Thermal / ZPL printer (labels):** Must be set to a RAW or ZPL port — **NOT** a Windows GDI
driver. Hermes sends raw ZPL bytes directly, bypassing the driver. If your Zebra printer is
configured as a Windows GDI driver, the label will print as garbled text. Use the Zebra
Setup Utilities to install the printer with the "ZPL" port type.

## Failure Handling

Print failures **never fail the order**.

- If warehouse PO print fails → audit log entry + escalation email to `ESCALATION_EMAIL`
- The order stays `ENTERED` and processing continues normally
- Emmanuel will see: "[Hermes] Action Required" email with the error detail
- Manual recovery: `python scripts/printer_tool.py --print logs/invoices/<id>.pdf`

Hermes does NOT retry prints automatically. If the printer is offline, fix it and
re-run manually.

## ZPL Label Flow

```
adapters/gs1_128_label.py::generate_label_zpl()
    → zpl string
    → adapters/gs1_128_label.py::print_label(zpl, printer_name)
        → subprocess: scripts/printer_tool.py --print-zpl-string "..." --printer NAME
            → win32print.WritePrinter() [RAW datatype]
```

All ZPL is transmitted as raw bytes — Zebra firmware interprets it directly.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Printer control requires Windows + pywin32" | pywin32 not installed | `pip install pywin32` |
| Printer not in `--list` output | Not installed in Windows | Add via Settings > Bluetooth & devices > Printers |
| PDF prints blank or garbled | Driver not PCL/PostScript | Check driver type in printer properties |
| ZPL label prints as text | Printer in GDI mode instead of RAW/ZPL | Reinstall with Zebra Setup Utilities, select ZPL port |
| "Access is denied" error | No print permission | Run as administrator or add user to print queue ACL |
| Job disappears from queue instantly | Printer offline | Bring printer online; check paper/ribbon |

## Obsidian Links
- [[brain/CAPABILITIES]] | [[brain/HERMES]] | [[skills/computer-control/SKILL]]
