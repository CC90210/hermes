"""
scripts/a2000_record.py
-----------------------
Interactive recipe recorder for the A2000 desktop adapter.

Run this on Emmanuel's machine, with A2000 open and a sample order ready.
The script prompts you through a guided session, capturing the click,
keystroke, and verify steps that make up "enter one new order."

The output is saved to `storage/a2000_recipe.json` (or wherever
`A2000_RECIPE_PATH` points) — the same file the desktop adapter reads at
runtime.

Usage:
    python scripts/a2000_record.py                       # interactive
    python scripts/a2000_record.py --output ./recipe.json
    python scripts/a2000_record.py --validate            # validate existing
    python scripts/a2000_record.py --dry-run             # replay without arming

Recipe format (JSON):

    {
      "version": "1",
      "recorded_at": "2026-04-27T20:30:00Z",
      "recorded_against": "A2000 v9.4 — Lowinger Distribution",
      "steps": [
        {"action": "focus"},
        {"action": "click",  "target": "MainMenu_NewOrder"},
        {"action": "wait",   "timeout_ms": 1000},
        {"action": "type",   "value": "{{customer_name}}"},
        {"action": "key",    "value": "{TAB}"},
        {"action": "verify", "value": "{{customer_name}}"},
        {"action": "type",   "value": "{{po_number}}"}
      ]
    }

Field substitutions (rendered at runtime by adapters/a2000_desktop.py):
    {{po_number}}, {{customer_name}}, {{customer_email}},
    {{customer_address}}, {{ship_to_address}}, {{order_date}},
    {{ship_date}}, {{notes}}

For each line item the adapter loops the steps inside a `loop_lines` block
(future enhancement — for now record the per-line steps inline and the
adapter will run them once per line item).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

DEFAULT_OUTPUT = Path(os.environ.get("A2000_RECIPE_PATH", "./storage/a2000_recipe.json"))

VALID_ACTIONS = ("focus", "click", "type", "key", "wait", "screenshot", "verify")
SUBSTITUTIONS = (
    "{{po_number}}", "{{customer_name}}", "{{customer_email}}",
    "{{customer_address}}", "{{ship_to_address}}", "{{order_date}}",
    "{{ship_date}}", "{{notes}}",
)


def _prompt(text: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{text}{suffix}: ").strip()
    return val or default


def _record_step(idx: int) -> dict | None:
    print(f"\n--- Step {idx + 1} ---")
    print("Actions: focus, click, type, key, wait, screenshot, verify  (or 'done')")
    action = _prompt("Action").lower()
    if action in ("done", "quit", "exit", ""):
        return None
    if action not in VALID_ACTIONS:
        print(f"  Invalid action {action!r}. Try again.")
        return _record_step(idx)

    step: dict = {"action": action}

    if action == "click":
        step["target"] = _prompt("Control auto_id (find via Inspect.exe or Spy++)")
    elif action == "type":
        print(f"  Substitutions available: {', '.join(SUBSTITUTIONS)}")
        step["value"] = _prompt("Text to type (use {{po_number}} etc. for runtime substitution)")
    elif action == "key":
        print("  Examples: {TAB}, {ENTER}, {F4}, ^s (Ctrl+S), %{F4} (Alt+F4)")
        step["value"] = _prompt("Key sequence")
    elif action == "wait":
        ms = _prompt("Wait milliseconds", "1000")
        step["timeout_ms"] = int(ms)
    elif action == "verify":
        print(f"  Substitutions available: {', '.join(SUBSTITUTIONS)}")
        step["value"] = _prompt("Text that must be visible on screen for the step to pass")
    elif action == "screenshot":
        pass  # no extra args

    print(f"  Recorded: {json.dumps(step, ensure_ascii=False)}")
    return step


def record_interactive(output: Path) -> None:
    print("=" * 70)
    print("A2000 RECIPE RECORDER")
    print("=" * 70)
    print(
        "Walk through the order-entry flow on A2000 step by step. After each\n"
        "manual action you take in A2000, describe it here. Use 'done' when\n"
        "the order is fully entered.\n"
    )
    recorded_against = _prompt(
        "Description (e.g. 'A2000 v9.4 — Lowinger Distribution')",
        "A2000 — unspecified",
    )

    steps: list[dict] = []
    idx = 0
    while True:
        step = _record_step(idx)
        if step is None:
            break
        steps.append(step)
        idx += 1

    if not steps:
        print("No steps recorded — aborting.")
        return

    recipe = {
        "version": "1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "recorded_against": recorded_against,
        "steps": steps,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(recipe, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ Wrote {len(steps)} steps to {output}")
    print("  Validate with: python scripts/a2000_record.py --validate")


def validate(path: Path) -> int:
    if not path.exists():
        print(f"✗ Recipe not found: {path}")
        return 1
    try:
        recipe = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"✗ Invalid JSON: {exc}")
        return 1

    steps = recipe.get("steps", [])
    if not steps:
        print(f"✗ Recipe has no steps")
        return 1

    errors: list[str] = []
    for idx, step in enumerate(steps):
        if "action" not in step:
            errors.append(f"step {idx}: missing 'action'")
            continue
        if step["action"] not in VALID_ACTIONS:
            errors.append(f"step {idx}: invalid action {step['action']!r}")
        if step["action"] == "click" and not step.get("target"):
            errors.append(f"step {idx}: 'click' requires 'target'")
        if step["action"] in ("type", "key", "verify") and not step.get("value"):
            errors.append(f"step {idx}: {step['action']!r} requires 'value'")

    print(f"Recipe: {path}")
    print(f"Recorded against: {recipe.get('recorded_against', 'unknown')}")
    print(f"Recorded at:      {recipe.get('recorded_at', 'unknown')}")
    print(f"Steps:            {len(steps)}")
    if errors:
        print(f"\n✗ {len(errors)} validation error(s):")
        for e in errors:
            print(f"   - {e}")
        return 1
    print(f"\n✓ Recipe is valid.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="A2000 recipe recorder + validator")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Where to write the recipe (default: A2000_RECIPE_PATH or ./storage/a2000_recipe.json)")
    parser.add_argument("--validate", action="store_true",
                        help="Validate the existing recipe without recording")
    args = parser.parse_args()

    if args.validate:
        return validate(args.output)

    record_interactive(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
