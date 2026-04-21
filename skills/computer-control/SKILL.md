---
name: computer-control
description: How Hermes uses OS-level capabilities — notifications, folder watching, file opening, clipboard, screenshots
tags: [hermes, skills, system, phase-2c]
---

# SKILL — Computer Control

> How Hermes interacts with the operating system. All calls go through `scripts/system_tool.py`.
> Hermes NEVER issues destructive OS commands directly.

## Desktop Notifications

**When Hermes triggers a notification:**

| Event | Notification | Urgency |
|-------|-------------|---------|
| Order entry failed after 3 retries | "Hermes — Action Required: Order #X failed" | High |
| Chargeback dispute window < 48 hours | "Hermes — Chargeback Deadline: PO #X expires in Xh" | High |
| Warehouse PO print failed | "Hermes — Print Failed: Order #X" | Normal |
| Manual approval needed (credit hold, unusual PO) | "Hermes — Needs Approval: [detail]" | Normal |

**When Hermes does NOT send notifications:**
- Normal successful order processing (that's what the audit log is for)
- Routine health check pings
- Low-priority informational events

Notifications require `HERMES_DESKTOP_NOTIFICATIONS=1` (default). Set to `0` to suppress.

**CLI:**
```bash
python scripts/system_tool.py --notify "Title" "Body"
python scripts/system_tool.py --notify "Critical" "Order failed" --urgent
```

## Folder Watcher

Used when IMAP is blocked or unreliable. Emmanuel drops PO files into a designated
folder; Hermes detects them and processes them through the normal pipeline.

**Enable by setting:**
```
HERMES_PO_DROP_FOLDER=C:\Users\Emmanuel\Desktop\PO-Inbox
```

**How it works:**
1. `watchdog.Observer` monitors the folder for `on_created` events
2. New `.pdf`, `.xlsx`, or `.csv` files matching the pattern trigger a pipeline run
3. Event is emitted as a JSON line on stdout: `{"event": "file_created", "path": "...", "timestamp": "..."}`
4. If `--action` is set, the command runs with `$FILE` substituted

**CLI (one-shot check):**
```bash
python scripts/system_tool.py --watch "C:\Users\Emmanuel\Desktop\PO-Inbox" --pattern "*.pdf"
```

**CLI (run forever until Ctrl-C):**
```bash
python scripts/system_tool.py --watch "C:\Users\Emmanuel\Desktop\PO-Inbox" --pattern "*.pdf" --forever --action "python scripts/po_tool.py --ingest $FILE"
```

## Opening Files

Hermes can open a file in its default application — used on escalation so Emmanuel
can inspect a failed PO without navigating the filesystem manually.

```bash
python scripts/system_tool.py --open "logs/invoices/42.pdf"
```

On Windows: uses `os.startfile()`. Opens PDF in the default viewer, Excel in Excel, etc.

**Safety:** paths with `..` that escape the project or user home are rejected.

## Clipboard

Read/write clipboard text — used by Hermes when preparing data for Emmanuel to paste
into another system (e.g., A2000 manual entry fallback).

```bash
python scripts/system_tool.py --clipboard-read
python scripts/system_tool.py --clipboard-write "PO-2026-04567"
```

## Screenshots

Captures the full screen to a PNG. Used when escalating UI errors in A2000 Playwright mode — Hermes can screenshot the failure state for Emmanuel to review.

```bash
python scripts/system_tool.py --screenshot
python scripts/system_tool.py --screenshot --output logs/a2000_error.png
```

Default output: `logs/screenshot_<UTC timestamp>.png`

## Hard Boundaries — What Hermes NEVER Does

Hermes is permitted to READ and OPEN files, send notifications, and watch folders.
It is **categorically forbidden** from:

- Running `del`, `rm`, `rmdir`, `format`, `shutdown`, `reboot`, `taskkill`
- Uninstalling or modifying system applications
- Changing printer defaults without explicit confirmation from Emmanuel
- Running arbitrary shell commands via `--action` unless the command starts with
  `python scripts/` (whitelisted) or `HERMES_UNSAFE_ACTIONS=1` is explicitly set
- Writing outside the project directory or user home

Every system call is:
1. Validated against path/action whitelists in `system_tool.py`
2. Audit-logged to `audit_log` with timestamp and details
3. Wrapped in try/except — failures are reported, not silently swallowed

## Dependencies

| Feature | Library | Install |
|---------|---------|---------|
| Notifications | plyer | `pip install plyer` |
| Notifications (fallback) | win10toast | `pip install win10toast` |
| Folder watcher | watchdog | `pip install watchdog` |
| Clipboard | pyperclip | `pip install pyperclip` |
| Screenshot | Pillow | `pip install Pillow` |

All are optional — each feature degrades independently if its library is missing.

## Obsidian Links
- [[brain/CAPABILITIES]] | [[brain/HERMES]] | [[skills/printing/SKILL]]
