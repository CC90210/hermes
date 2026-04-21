"""
scripts/system_tool.py
----------------------
Desktop-level system operations for Hermes:
  - Desktop notifications
  - Opening files with their default app
  - Watching a folder for new files (PO drop-folder fallback)
  - Clipboard read/write
  - Screenshots

Each feature is independently wrapped; a missing optional library only
disables that feature — everything else keeps working.

Usage:
    python scripts/system_tool.py --notify "Title" "Body" [--urgent]
    python scripts/system_tool.py --open <file_or_url>
    python scripts/system_tool.py --watch <folder> [--pattern "*.pdf"] [--forever] [--action CMD]
    python scripts/system_tool.py --clipboard-read
    python scripts/system_tool.py --clipboard-write "text"
    python scripts/system_tool.py --screenshot [--output path.png]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Safety constants
# ---------------------------------------------------------------------------

# Action commands that run on folder-watch events must start with one of these
# prefixes, OR the operator must set HERMES_UNSAFE_ACTIONS=1.
_SAFE_ACTION_PREFIXES = ("python scripts/",)


def _is_safe_path(raw: str) -> bool:
    """Reject paths that escape project/user directories via '..' traversal."""
    try:
        resolved = Path(raw).resolve()
        # Allow paths inside project root or user home
        project_root = Path(__file__).resolve().parent.parent
        user_home = Path.home()
        return resolved.is_relative_to(project_root) or resolved.is_relative_to(user_home)
    except Exception:  # noqa: BLE001
        return False


def _is_safe_action(cmd: str) -> bool:
    if os.environ.get("HERMES_UNSAFE_ACTIONS", "0") == "1":
        return True
    return any(cmd.startswith(p) for p in _SAFE_ACTION_PREFIXES)


# ---------------------------------------------------------------------------
# Audit logging helper (best-effort, never raises)
# ---------------------------------------------------------------------------


def _audit(action: str, details: dict[str, Any]) -> None:
    try:
        db_path_str = os.environ.get("DB_PATH", "./storage/lowinger.db")
        db_path = Path(db_path_str)
        if not db_path.exists():
            return

        import asyncio as _asyncio

        from storage.db import log_audit as _log_audit

        async def _write() -> None:
            await _log_audit(db_path, agent_name="system_tool", action=action, details=details)

        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_write())
            else:
                loop.run_until_complete(_write())
        except RuntimeError:
            _asyncio.run(_write())
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def _strip_crlf(text: str) -> str:
    """Remove carriage returns and newlines from user-supplied strings."""
    return re.sub(r"[\r\n]", " ", text).strip()


def send_notification(title: str, message: str, urgent: bool = False) -> dict[str, Any]:
    """Send a desktop notification.

    Tries plyer first (cross-platform), then win10toast on Windows.
    Returns a result dict with success/error keys.
    """
    title = _strip_crlf(title)
    message = _strip_crlf(message)

    try:
        from plyer import notification  # type: ignore[import]

        notification.notify(
            title=title,
            message=message,
            timeout=10 if not urgent else 0,
        )
        _audit("notification_sent", {"title": title, "urgent": urgent})
        return {"success": True, "backend": "plyer"}
    except Exception as plyer_exc:  # noqa: BLE001
        # Fallback: win10toast on Windows
        if sys.platform == "win32":
            try:
                from win10toast import ToastNotifier  # type: ignore[import]

                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10, threaded=True)
                _audit("notification_sent", {"title": title, "urgent": urgent, "backend": "win10toast"})
                return {"success": True, "backend": "win10toast"}
            except Exception as toast_exc:  # noqa: BLE001
                error = f"plyer failed: {plyer_exc}; win10toast failed: {toast_exc}"
        else:
            error = f"plyer failed: {plyer_exc}; win10toast not available on this platform"

    _audit("notification_failed", {"title": title, "error": error})
    return {"success": False, "error": error}


# ---------------------------------------------------------------------------
# Open file / URL
# ---------------------------------------------------------------------------


def open_file(path: str) -> dict[str, Any]:
    """Open a file or URL with its default application.

    Rejects paths with '..' that could escape safe directories.
    """
    if ".." in path and not _is_safe_path(path):
        return {"success": False, "error": "Path rejected: unsafe traversal detected"}

    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=True)
        else:
            subprocess.run(["xdg-open", path], check=True)

        _audit("open_file", {"path": path})
        return {"success": True, "path": path}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Folder watcher
# ---------------------------------------------------------------------------


def watch_folder(
    folder: str,
    pattern: str = "*",
    forever: bool = False,
    action: str | None = None,
) -> None:
    """Watch a folder and emit JSON events on stdout when new files appear.

    If ``action`` is provided, runs the command with $FILE substituted.
    The watcher runs until KeyboardInterrupt (if forever=True) or one scan
    (if forever=False — useful for one-shot CI checks).
    """
    try:
        from watchdog.events import FileSystemEventHandler, FileCreatedEvent  # type: ignore[import]
        from watchdog.observers import Observer  # type: ignore[import]
    except ImportError:
        print(
            json.dumps({"error": "watchdog not installed. Run: pip install watchdog"}),
            flush=True,
        )
        return

    if ".." in folder and not _is_safe_path(folder):
        print(json.dumps({"error": "Folder path rejected: unsafe traversal detected"}), flush=True)
        return

    if action and not _is_safe_action(action):
        print(
            json.dumps({
                "error": (
                    f"Action '{action}' is not in the whitelist. "
                    "It must start with 'python scripts/' or set HERMES_UNSAFE_ACTIONS=1"
                )
            }),
            flush=True,
        )
        return

    import fnmatch

    class _Handler(FileSystemEventHandler):
        def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
            if event.is_directory:
                return
            file_path = str(event.src_path)
            if not fnmatch.fnmatch(Path(file_path).name, pattern):
                return

            payload = {
                "event": "file_created",
                "path": file_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            print(json.dumps(payload), flush=True)
            _audit("folder_watch_event", payload)

            if action:
                cmd = action.replace("$FILE", file_path)
                try:
                    subprocess.Popen(cmd, shell=True)  # noqa: S602 — guarded by whitelist
                except Exception as exc:  # noqa: BLE001
                    print(json.dumps({"error": f"Action failed: {exc}"}), flush=True)

    observer = Observer()
    observer.schedule(_Handler(), path=folder, recursive=False)
    observer.start()

    try:
        if forever:
            while True:
                time.sleep(1)
        else:
            time.sleep(2)  # Give one scan cycle
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


def clipboard_read() -> dict[str, Any]:
    """Read text from the system clipboard."""
    try:
        import pyperclip  # type: ignore[import]

        text = pyperclip.paste()
        return {"success": True, "text": text}
    except ImportError:
        return {"success": False, "error": "pyperclip not installed. Run: pip install pyperclip"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


def clipboard_write(text: str) -> dict[str, Any]:
    """Write text to the system clipboard."""
    try:
        import pyperclip  # type: ignore[import]

        pyperclip.copy(text)
        _audit("clipboard_write", {"length": len(text)})
        return {"success": True}
    except ImportError:
        return {"success": False, "error": "pyperclip not installed. Run: pip install pyperclip"}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


def take_screenshot(output_path: str | None = None) -> dict[str, Any]:
    """Capture the full screen and save to disk.

    Default output: logs/screenshot_<timestamp>.png
    """
    try:
        from PIL import ImageGrab  # type: ignore[import]
    except ImportError:
        return {
            "success": False,
            "error": "Pillow not installed. Run: pip install Pillow",
        }

    if output_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(logs_dir / f"screenshot_{ts}.png")

    if ".." in output_path and not _is_safe_path(output_path):
        return {"success": False, "error": "Output path rejected: unsafe traversal detected"}

    try:
        img = ImageGrab.grab()
        img.save(output_path)
        _audit("screenshot", {"path": output_path})
        return {"success": True, "path": output_path}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes system operations — notifications, folder watch, open files"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--notify", nargs=2, metavar=("TITLE", "BODY"), help="Send a desktop notification")
    group.add_argument("--open", metavar="PATH", dest="open_path", help="Open a file or URL")
    group.add_argument("--watch", metavar="FOLDER", help="Watch a folder for new files")
    group.add_argument("--clipboard-read", action="store_true")
    group.add_argument("--clipboard-write", metavar="TEXT")
    group.add_argument("--screenshot", action="store_true")

    parser.add_argument("--urgent", action="store_true", help="Sticky notification (--notify only)")
    parser.add_argument("--pattern", default="*", help="File pattern for --watch (e.g. '*.pdf')")
    parser.add_argument("--forever", action="store_true", help="Keep --watch running until Ctrl-C")
    parser.add_argument("--action", metavar="CMD", help="Command to run on new file (use $FILE)")
    parser.add_argument("--output", metavar="PATH", help="Output path for --screenshot")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")

    args = parser.parse_args()

    def _out(data: dict[str, Any]) -> None:
        if args.as_json:
            print(json.dumps(data))
        else:
            for k, v in data.items():
                print(f"{k}: {v}")

    if args.notify:
        title, body = args.notify
        result = send_notification(title, body, urgent=args.urgent)
        _out(result)
        return 0 if result.get("success") else 1

    if args.open_path:
        result = open_file(args.open_path)
        _out(result)
        return 0 if result.get("success") else 1

    if args.watch:
        # watch_folder streams JSON lines; no single final output
        watch_folder(args.watch, pattern=args.pattern, forever=args.forever, action=args.action)
        return 0

    if args.clipboard_read:
        result = clipboard_read()
        if args.as_json:
            print(json.dumps(result))
        else:
            if result.get("success"):
                print(result.get("text", ""))
            else:
                print(result.get("error", ""), file=sys.stderr)
        return 0 if result.get("success") else 1

    if args.clipboard_write is not None:
        result = clipboard_write(args.clipboard_write)
        _out(result)
        return 0 if result.get("success") else 1

    if args.screenshot:
        result = take_screenshot(output_path=args.output)
        _out(result)
        return 0 if result.get("success") else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
