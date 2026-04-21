---
description: Print a file (warehouse PO, invoice, carton label) to a specified printer
---

Parse $ARGUMENTS as "<file_path> [printer_name]".

Split on the first space that is followed by a non-path character to separate file_path from
optional printer_name. If printer_name contains spaces it must be quoted.

Route by file extension:

If file ends in .zpl:
  Route to thermal (ZPL) printer:
  python scripts/printer_tool.py --print-zpl "$file" --printer "$printer" --json
  (if no printer_name, use LABEL_PRINTER_NAME from env; if still blank, error — thermal printer name is required)

If file ends in .pdf, .docx, .doc, .txt, or any other document format:
  Route to regular printer:
  python scripts/printer_tool.py --print "$file" [--printer "$printer"] --json
  (if no printer_name, uses system default)

Report back to Emmanuel:
- Job ID (if returned by spooler)
- Printer name used
- "Sent to spooler" or the error message
- For PDFs: note that page count is not available via ShellExecute (it is sent to the driver)

Examples:
  /print logs/invoices/42.pdf
  /print logs/invoices/42.pdf "HP LaserJet Pro"
  /print labels/carton_001.zpl "ZDesigner ZT411-300dpi ZPL"