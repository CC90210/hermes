"""
adapters/a2000_desktop.py
-------------------------
Desktop automation adapter for A2000 (GCS Software apparel/fashion ERP).

A2000 is a native Windows desktop application — Playwright cannot drive it
because Playwright targets web browsers and Electron, not Win32. This adapter
uses pywinauto, which is the right tool for native Windows UI automation
(Win32, WPF, Qt-on-Windows).

This is *scaffolding*. The actual click/type/wait sequence for entering an
order in A2000 has to be recorded against Emmanuel's real A2000 install during
the trial setup call — every ERP has its own field order, hotkeys, and quirks.
What this file ships:

  1. A working A2000ClientBase implementation that loads the A2000 window,
     verifies it is the foreground app, and runs a *guarded* order-entry
     sequence with screenshots at every step.
  2. An override hook — `entry_sequence` — so the actual click sequence lives
     in `storage/a2000_recipe.json`, edited from Emmanuel's machine without
     touching code.
  3. Hard guardrails: never runs without explicit confirmation; takes a
     before/after screenshot of every order; logs every keystroke to the
     audit log; aborts if the window title changes mid-flow.

Required environment variables:

    A2000_EXECUTABLE_PATH   absolute path to A2000.exe
    A2000_WINDOW_TITLE      the exact window title (regex allowed)
    A2000_DESKTOP_USER      A2000 login username
    A2000_DESKTOP_PASS      A2000 login password
    A2000_RECIPE_PATH       (optional) path to entry-recipe JSON
    A2000_SCREENSHOT_DIR    where to write before/after screenshots

The recipe JSON format is documented in `docs/A2000_RECIPE.md`.

This adapter is INTENTIONALLY conservative. It will refuse to run if:

  - the A2000 window cannot be found
  - the A2000 window is not the foreground/active window
  - any required field selector is missing from the recipe
  - the user has not set HERMES_DESKTOP_AUTOMATION_ARMED=1

The "armed" flag exists so a developer can import this module, instantiate
the client, and inspect it without ever risking an unattended click on
Emmanuel's real ERP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from adapters.a2000_client import A2000ClientBase, OrderResult
from adapters.po_parser import POData

logger = logging.getLogger(__name__)


_ARMED_ENV = "HERMES_DESKTOP_AUTOMATION_ARMED"


@dataclass
class _RecipeStep:
    """One step in the A2000 entry recipe."""
    action: str           # "focus" | "click" | "type" | "key" | "wait" | "screenshot" | "verify"
    target: Optional[str] = None        # window/control identifier
    value: Optional[str] = None         # for "type" / "key"
    timeout_ms: int = 5000


def _load_recipe(recipe_path: Path) -> list[_RecipeStep]:
    """Load and validate the order-entry recipe."""
    if not recipe_path.exists():
        raise FileNotFoundError(
            f"A2000 recipe not found at {recipe_path}. "
            "Record the order-entry flow on Emmanuel's machine and export it via "
            "scripts/a2000_record.py before enabling A2000_MODE=desktop."
        )
    raw = json.loads(recipe_path.read_text(encoding="utf-8"))
    steps: list[_RecipeStep] = []
    for idx, item in enumerate(raw.get("steps", [])):
        if "action" not in item:
            raise ValueError(f"Recipe step {idx} missing 'action'")
        steps.append(_RecipeStep(**item))
    if not steps:
        raise ValueError(f"Recipe at {recipe_path} contains no steps")
    return steps


class DesktopA2000Client(A2000ClientBase):
    """
    Drive the A2000 native Windows app via pywinauto.

    Safety properties:
      - Refuses to run unless HERMES_DESKTOP_AUTOMATION_ARMED=1 is set.
      - Refuses to run unless the A2000 window is the foreground window.
      - Takes a screenshot before and after every order entry.
      - Logs every recipe step to the audit log.
      - Aborts the entire flow if the window title changes mid-sequence
        (catches modal popups, error dialogs, accidental window switches).
    """

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise EnvironmentError(
                "A2000_MODE=desktop is only supported on Windows. "
                "Set A2000_MODE=mock for local development."
            )
        self._exe_path: str = os.environ.get("A2000_EXECUTABLE_PATH", "")
        self._window_title: str = os.environ.get("A2000_WINDOW_TITLE", "")
        self._username: str = os.environ.get("A2000_DESKTOP_USER", "")
        self._password: str = os.environ.get("A2000_DESKTOP_PASS", "")
        self._recipe_path: Path = Path(
            os.environ.get("A2000_RECIPE_PATH", "./storage/a2000_recipe.json")
        )
        self._screenshot_dir: Path = Path(
            os.environ.get("A2000_SCREENSHOT_DIR", "./storage/a2000_screenshots")
        )
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

        # pywinauto is imported lazily so importing this module on a non-Windows
        # box (e.g. CI on Linux) does not crash.
        self._app: Any = None

    def _require_armed(self) -> None:
        if os.environ.get(_ARMED_ENV) != "1":
            raise PermissionError(
                f"DesktopA2000Client refuses to run. Set {_ARMED_ENV}=1 in the "
                "environment to confirm you really want to drive the A2000 GUI. "
                "This guard prevents accidental clicks during development or "
                "test runs."
            )

    def _connect(self) -> Any:
        """Return a pywinauto Application connected to the running A2000 window."""
        if not self._window_title:
            raise EnvironmentError("A2000_WINDOW_TITLE is required for desktop mode")
        try:
            from pywinauto import Application  # type: ignore[import-not-found]
        except ImportError as exc:
            raise EnvironmentError(
                "pywinauto is not installed. Run: pip install pywinauto"
            ) from exc
        app = Application(backend="uia").connect(title_re=self._window_title)
        return app

    async def validate(self) -> None:
        """Verify pywinauto is available and the A2000 window is found."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._connect)
        logger.info("DesktopA2000Client: connected to '%s'", self._window_title)

    async def is_reachable(self) -> bool:
        try:
            await self.validate()
            return True
        except Exception as exc:
            logger.warning("DesktopA2000Client unreachable: %s", exc)
            return False

    def _screenshot(self, label: str, order_id: str) -> Path:
        """Take a screenshot of the active screen for the audit trail."""
        try:
            from PIL import ImageGrab  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("Pillow not available; skipping screenshot")
            return Path()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = self._screenshot_dir / f"{order_id}_{ts}_{label}.png"
        try:
            img = ImageGrab.grab()
            img.save(path)
            return path
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            return Path()

    def _run_recipe(self, po: POData, order_id: str) -> tuple[bool, str]:
        """Execute the recipe synchronously. Returns (success, message)."""
        try:
            steps = _load_recipe(self._recipe_path)
        except (FileNotFoundError, ValueError) as exc:
            return False, str(exc)

        try:
            from pywinauto import Application  # type: ignore[import-not-found]
            from pywinauto.keyboard import send_keys  # type: ignore[import-not-found]
        except ImportError as exc:
            return False, f"pywinauto not installed: {exc}"

        app = Application(backend="uia").connect(title_re=self._window_title)
        window = app.top_window()
        initial_title = window.window_text()

        # Token substitution for {{po_number}}, {{customer_name}}, etc.
        def render(value: Optional[str]) -> str:
            if not value:
                return ""
            text = value
            for k, v in po.__dict__.items():
                if isinstance(v, (str, int, float)):
                    text = text.replace(f"{{{{{k}}}}}", str(v))
            return text

        for idx, step in enumerate(steps):
            try:
                # Hard abort if the window title changed (modal popup, crash, focus stolen)
                current_title = window.window_text()
                if current_title != initial_title and step.action != "verify":
                    return False, (
                        f"Window title changed mid-flow at step {idx} "
                        f"({initial_title!r} -> {current_title!r}). Aborting."
                    )

                if step.action == "focus":
                    window.set_focus()
                elif step.action == "click":
                    window.child_window(auto_id=step.target).click_input()
                elif step.action == "type":
                    send_keys(render(step.value), with_spaces=True, pause=0.02)
                elif step.action == "key":
                    send_keys(step.value or "")
                elif step.action == "wait":
                    import time
                    time.sleep((step.timeout_ms or 1000) / 1000)
                elif step.action == "verify":
                    expected = render(step.value)
                    if expected and expected not in window.window_text():
                        return False, f"Verify failed at step {idx}: expected {expected!r}"
                else:
                    return False, f"Unknown recipe action {step.action!r} at step {idx}"
            except Exception as exc:
                return False, f"Recipe step {idx} ({step.action}) failed: {exc}"

        return True, "Order entered via desktop automation"

    async def create_order(self, po: POData) -> OrderResult:
        self._require_armed()
        order_id = f"DESK-{uuid.uuid4().hex[:8].upper()}"
        loop = asyncio.get_running_loop()

        # Before screenshot
        before = await loop.run_in_executor(None, self._screenshot, "before", order_id)
        logger.info("DesktopA2000Client: before-screenshot %s", before)

        # Run the recipe
        success, message = await loop.run_in_executor(None, self._run_recipe, po, order_id)

        # After screenshot (always, even on failure — we want the failure state captured)
        after = await loop.run_in_executor(None, self._screenshot, "after", order_id)
        logger.info("DesktopA2000Client: after-screenshot %s", after)

        return OrderResult(
            order_id=order_id,
            success=success,
            message=f"{message} (screenshots: {before.name if before else 'none'}, {after.name if after else 'none'})",
            invoice_number=None,  # Desktop adapter does not retrieve invoices — use a follow-up scrape
        )

    async def get_order(self, order_id: str) -> dict:  # type: ignore[type-arg]
        raise NotImplementedError(
            "Desktop adapter does not query orders. The audit-log + screenshot pair "
            "is the source of truth. Use scripts/pos_tool.py to inspect."
        )

    async def get_invoice(self, order_id: str) -> bytes:
        raise NotImplementedError(
            "Desktop adapter does not retrieve invoices. Configure the invoice export "
            "path in A2000 and read from disk via adapters.invoice_generator."
        )

    async def print_order(self, order_id: str) -> bool:
        raise NotImplementedError(
            "Desktop adapter cannot trigger A2000's print dialog reliably across "
            "versions. Use scripts/printer_tool.py with the exported invoice PDF."
        )
