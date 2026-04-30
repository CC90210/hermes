# A2000 Desktop Recipe

Hermes can drive the native A2000 Windows app through `pywinauto`, but only after
the exact order-entry flow has been recorded on the client's machine. A recipe
is a JSON file that lists the safe focus, click, type, key, wait, screenshot,
and verify steps needed to enter one order.

Default path:

```text
storage/a2000_recipe.json
```

Record or validate the recipe from the Hermes repo:

```powershell
.venv\Scripts\python.exe scripts\a2000_record.py
.venv\Scripts\python.exe scripts\a2000_record.py --validate
```

Hermes will not click inside A2000 unless all of these are true:

- `A2000_MODE=desktop`
- `A2000_EXECUTABLE_PATH` is set
- `A2000_WINDOW_TITLE` is set
- `storage/a2000_recipe.json` exists and validates
- `HERMES_DESKTOP_AUTOMATION_ARMED=1`

Recipe shape:

```json
{
  "version": "1",
  "recorded_at": "2026-04-27T20:30:00Z",
  "recorded_against": "A2000 - Lowinger Distribution",
  "steps": [
    {"action": "focus"},
    {"action": "click", "target": "MainMenu_NewOrder"},
    {"action": "wait", "timeout_ms": 1000},
    {"action": "type", "value": "{{customer_name}}"},
    {"action": "key", "value": "{TAB}"},
    {"action": "verify", "value": "{{customer_name}}"},
    {"action": "type", "value": "{{po_number}}"}
  ]
}
```

Supported substitutions:

- `{{po_number}}`
- `{{customer_name}}`
- `{{customer_email}}`
- `{{customer_address}}`
- `{{ship_to_address}}`
- `{{order_date}}`
- `{{ship_date}}`
- `{{notes}}`

Production rule: keep `HERMES_DESKTOP_AUTOMATION_ARMED=0` until a human has
watched a dry run on the real machine and confirmed the recipe lands in the
right A2000 fields.
