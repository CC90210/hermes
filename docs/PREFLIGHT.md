# Hermes — Preflight & Risk Register

> Read this **before** scheduling Emmanuel's setup call. Every item here is a
> failure mode that has either already bitten us or is rated likely-to-bite based
> on what's actually in the repo today (not what the docs claim).

---

## A. Dependency reality check

The `215 tests passing` claim is true **only after** `pip install -r requirements.txt`
on a Python 3.12 environment. A fresh checkout fails to collect tests because
`aiosqlite`, `respx`, `rich`, and `pytest-cov` are not in the system Python.

### What you must run on Emmanuel's machine, in order

```powershell
# 1. Verify Python (3.12 is what we're tested against)
python --version       # must be 3.12.x

# 2. Create a project-local venv so we never pollute his system Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies — wheels first, then any platform-specific extras
pip install --upgrade pip wheel
pip install -r requirements.txt

# 4. Verify the install actually worked
python -m pytest tests/ -q              # must show 215+ passed
python -m demo.run_demo                 # must complete in <1s, no Unicode errors

# 5. Smoke-test the CLI tools (these will warn about missing .env — that's fine)
python scripts/health_tool.py
python scripts/po_tool.py --list
```

If any of those steps fail, **stop and fix before going further.** Do not push
through with a half-installed system.

### Dependencies likely to bite

| Package | Why it bites | Mitigation |
|---------|--------------|------------|
| `pywin32` | Win32-only; build from wheel only — no source build on Windows without VS Build Tools | Use Python 3.12 (wheels exist); fall back to `pywin32-ctypes` if the wheel is missing |
| `pywinauto` | Win32-only; depends on `comtypes`; UAC-elevated A2000 will refuse automation from non-elevated session | Run Hermes from the same elevation level as A2000 |
| `Pillow` | Wheel for 3.12 is fine; older Python may need source build | Lock Python to 3.12 |
| `playwright` | Needs `playwright install chromium` after `pip install` | Run the install command in setup |
| `exchangelib` | OAuth flow can hang on Office 365 with MFA enforced | Test with a service account, not Emmanuel's user account |
| `imapclient` | Office 365 deprecated basic-auth IMAP — needs OAuth or App Password | Decide *before* the call: App Password or OAuth |
| `httpx` vs other tools | We pin `>=0.27.1`; existing system pips may have `0.28.x` (incompatible with `supabase`) | Project venv isolates it |

### Conflicts already in this environment

- `supabase 2.7.0 requires httpx<0.28` — conflicts with our `>=0.27.1`. **The project venv resolves this.** Do not `pip install` Hermes deps into Emmanuel's system Python.
- `mcp 1.26.0 requires httpx>=0.27.1` — satisfied.

---

## B. The four A2000 modes — what actually works today

A2000 is GCS Software's native **Windows desktop** ERP. That single fact dictates
which mode is viable:

| Mode | What it is | Status today | Use when |
|------|-----------|--------------|----------|
| `mock` | In-memory fake | ✅ Working | Demos, tests, CI |
| `api` | REST API client | ⚠️ Stubs only — `NotImplementedError` everywhere. Vendor API spec not provisioned | If/when GCS gives Emmanuel API credentials. Don't promise this until we've confirmed GCS sells the API module |
| `edi` | Writes X12 850 to disk for VAN/AS2 pickup | ✅ Working (write side); ❌ no inbound 855/810 reader yet | Only useful if Emmanuel has an EDI VAN (SPS, TrueCommerce, etc.) and a willing receiver |
| `playwright` | Browser automation | ❌ Stubs only. **A2000 is desktop, not web — Playwright is wrong tool** | If Emmanuel's A2000 install has a web/Electron front end (rare). Otherwise dead path |
| `desktop` | **NEW** — native Win32 automation via pywinauto | ✅ Scaffolding shipped. Recipe must be recorded on Emmanuel's A2000 | This is the realistic path for "computer functions to take full control of his software A2000" |

**Bottom line:** for a Walgreens-grade setup we'll either land on `desktop`
(driving the GCS app directly) or `edi` (going around it via VAN). The `api`
path is aspirational until we have a vendor commitment.

---

## C. The desktop adapter — what we shipped, what's missing

`adapters/a2000_desktop.py` (new) is the realistic path. It does this:

1. Locates the A2000 window by title regex (you set `A2000_WINDOW_TITLE`).
2. Refuses to run unless `HERMES_DESKTOP_AUTOMATION_ARMED=1` is explicitly set
   in the environment. (Hard safety gate — prevents accidental clicks from
   imports or test runs.)
3. Loads a JSON "recipe" of clicks/types/keys/waits from
   `storage/a2000_recipe.json`.
4. Takes a **before screenshot**, runs the recipe, takes an **after
   screenshot** — every order entry produces an audit trail.
5. Aborts immediately if the window title changes mid-flow (catches modal
   popups, error dialogs, focus theft).

### What's still required before this works on Emmanuel's machine

- [ ] **Record the entry sequence on his A2000 install.** Every ERP has unique
      field order, hotkeys, and tab traversal. We need to sit at his keyboard,
      record each step, and produce a `storage/a2000_recipe.json`.
      No amount of reading docs substitutes for recording it live.
- [ ] **Confirm A2000 is *not* UAC-elevated.** If it runs as Administrator,
      our automation must also run elevated, which means running Hermes as a
      service account with matching rights.
- [ ] **Confirm A2000 has no anti-automation protections.** Most legacy ERPs
      don't; some healthcare-adjacent ones do.
- [ ] **Decide where invoices land.** A2000 typically exports invoices as PDFs
      to a configurable folder. We need that folder path so the invoice agent
      can pick them up — the desktop adapter does *not* try to scrape the
      invoice from the GUI (too fragile).
- [ ] **Add a `scripts/a2000_record.py`** that records a recipe interactively.
      *Not yet written.* Workaround for the trial: hand-edit the JSON.

### What can go wrong, and what we do about it

| Risk | Likelihood | Impact | Mitigation in code |
|------|-----------|--------|-------------------|
| Modal popup steals focus mid-entry | High | Wrong field gets the input; potentially overwrites real data | Window-title-change abort + before/after screenshot |
| A2000 update changes field tab order | Medium | Recipe goes stale silently | Recipe versioning + `verify` steps that check for expected text |
| Network glitch causes A2000 to hang | Medium | Pipeline blocks | `timeout_ms` per recipe step + orchestrator-level retry budget |
| User clicks A2000 while Hermes is running | Medium | Race condition on the active window | Foreground check before each step + abort on title mismatch |
| Wrong customer selected | Low (with verify steps) | Wrong-customer order — financial damage | `verify` recipe steps must confirm customer name appears before submit |
| Screenshots fill the disk | Low | Disk fills, pipeline fails | Add a retention policy in `scripts/state_sync.py` (TODO) |
| `HERMES_DESKTOP_AUTOMATION_ARMED` accidentally left set in dev | Medium | Real clicks during testing | The flag is per-environment, not committed. Recipe path defaults to a non-existent file in dev |
| Two Hermes instances clash | Low | Both try to drive the GUI | Cron Hermes vs IDE Hermes already coordinate via `orders.status`. Add a desktop-mode lock file before any GUI write (TODO) |

---

## D. Email pipeline — the real-world pitfalls

| Pitfall | What happens | What to do |
|---------|--------------|------------|
| Office 365 disabled basic-auth IMAP for the tenant | `imapclient.login()` fails with cryptic "AUTHENTICATE failed" | **Decide before the call:** OAuth via `exchangelib`, or an App Password. Ask Emmanuel's IT |
| MFA enabled on the user account | Same — login fails | App Password (per-app credential) is the simplest workaround |
| Emmanuel uses Outlook desktop (.pst) not server-side IMAP | We can't poll a .pst file via IMAP | Folder-watcher fallback: `HERMES_PO_DROP_FOLDER` already wired |
| POs come from EDI, not email | Inbox sees nothing | Wire up an AS2/VAN drop folder to `HERMES_PO_DROP_FOLDER` |
| Email body has the PO inline (no attachment) | Current parser is biased toward attachments | Already handled — `email_agent` falls back to body text if no PO attachment |

---

## E. PO parsing — why accuracy matters and where it breaks

`adapters/po_parser.py` uses Ollama (`qwen2.5:32b`) by default. Ollama is **local** — which means:

- It needs to be *running* on Emmanuel's machine: `ollama serve` + the model pulled with `ollama pull qwen2.5:32b`.
- The 32B model needs ~20GB RAM. If his machine doesn't have it, switch to `qwen2.5:7b` (lower accuracy on edge cases).
- Cold-start latency is 5–10 seconds the first time. **Do `ollama run qwen2.5:32b` once before the demo** so the model is in memory.

### Accuracy breaks we've seen and the fix

| Break mode | Cause | Fix |
|-----------|-------|-----|
| Wrong PO number extracted (uses customer reference instead) | Two numbers on the page, prompt picks the wrong one | Prompt update: "po_number is the *vendor/buyer* PO reference, NOT the customer's internal req number" — already in `_EXTRACTION_PROMPT` |
| Quantities returned as float (e.g. `12.0`) when integer expected | LLM follows the unit ("12 EA" → "12.0") | DB column is `REAL`; coerce to int in `LineItem` constructor (✅ already integer-typed) |
| Apparel size/color matrix flattened wrong | A 3-size × 4-color matrix should expand to 12 lines, not 1 | `adapters/matrix_expander.py` handles this — but only when the prompt extracts the matrix structure. Verify on Emmanuel's first 5 POs |
| Ship date set to today when buyer wrote "ASAP" | LLM hallucinates a date | Confidence guardrail: if `ship_date` is the same as `order_date`, escalate for review |
| UPC mis-extracted (12 vs 13 digits) | Prompt says "12-digit" but EAN is 13 | Update prompt to accept 12 or 13 |

### Fallback path if Ollama is down

`USE_OLLAMA=0` makes `demo.run_demo` use a hardcoded mock parse. **The
production parser does not have a non-Ollama fallback** — if Ollama is down,
PO parsing fails. Add a `cloud_parser.py` that falls back to Anthropic/OpenAI
under the no-storage DPA. *(TODO — not in repo today.)*

---

## F. Pre-demo checklist (the night before)

```text
[ ] Python 3.12 installed and on PATH
[ ] python -m venv .venv && pip install -r requirements.txt — clean install
[ ] python -m pytest tests/ -q — 215+ passed, 0 failed
[ ] python -m demo.run_demo — clean run, no Unicode errors, <1s
[ ] cd demo && demo.bat — same demo via .bat file (chcp 65001 set)
[ ] python scripts/health_tool.py — no crashes (warnings about missing .env are fine)

If running the live Gmail → Google Sheet demo:
[ ] Google Cloud Console OAuth client created for Adon's Gmail
[ ] Service-account JSON for the target Google Sheet
[ ] Test sheet open in a browser tab — refresh shows last row updated
[ ] Test PO email pre-staged in Adon's inbox; refresh fetch confirms parser hit
[ ] Backup: terminal demo (`demo.bat`) ready in a second window in case the live demo hiccups

If running the desktop A2000 path:
[ ] HERMES_DESKTOP_AUTOMATION_ARMED is NOT set yet (we'll arm only after he okays it on the call)
[ ] storage/a2000_recipe.json exists and was recorded against his A2000 install
[ ] storage/a2000_screenshots/ exists and is writable
[ ] One dry-run on a sandbox order, both screenshots inspected
```

---

## G. Training the agent on Emmanuel's nuances — the 30-day plan

The 30-day trial isn't just runtime — it's **supervised learning**. Concretely:

### Week 1 — Calibration
- [ ] Capture 20+ historical POs from his inbox (with permission), tag each
      with the correct extraction (customer, line items, special terms).
- [ ] Run them through the parser. For every miss, add an example to the
      few-shot section of `_EXTRACTION_PROMPT` *or* add a regex post-processor
      in `adapters/po_parser.py`.
- [ ] Confirm the contract pricing table (`adapters/contract_price.py`)
      matches what's in his head. Pull every customer's price book.

### Week 2 — Shadow mode
- [ ] Pipeline runs against real inbound mail, but every order pauses at
      `PARSED` status — never enters A2000. Emmanuel reviews each parse,
      green-lights or corrects it. Corrections go to `memory/MISTAKES.md`.
- [ ] Track parse accuracy day-over-day. Goal: 95%+ by end of week 2.

### Week 3 — Supervised live
- [ ] First real orders enter A2000 (desktop adapter, armed). Hermes pauses
      *before submit* on every order for the first 50; Emmanuel hits Enter.
- [ ] Disable supervision per customer once that customer hits 20 clean orders.

### Week 4 — Autonomous + review
- [ ] Pipeline runs unsupervised for routine customers.
- [ ] Daily briefing surfaces every escalation, every drift, every chargeback risk.
- [ ] Day-30 review: pull the audit log, count the wins, count the misses,
      decide pricing.

### What to watch for

- **Distribution shift:** Walgreens changes their PO format in week 3 — accuracy
  drops 20%. Mitigation: weekly accuracy report flags the regression before
  Emmanuel notices.
- **Edge cases that look like the common case:** "PO" emails that are actually
  invoices from suppliers. The classifier needs negative examples too.
- **Trust collapse:** one wrong-customer order breaks 3 weeks of trust. The
  desktop-mode `verify` step on customer name is the single most important
  guardrail. Do not skip it.

---

## H. What's in the repo but not bulletproof yet

A short, honest list of "this works in tests but I would not bet a customer on it without one more pass":

| Item | Status | Risk |
|------|--------|------|
| `adapters/edi_855_ack.py` — PO acknowledgment | Works on the happy path | No retry/queue on transmission failure |
| `adapters/edi_856_asn.py` — ASN | Generates the file | No transmission scheduler — relies on whoever picks up `EDI_OUTPUT_DIR` |
| `adapters/gs1_128_label.py` — carton labels | Generates correct ZPL | Assumes Zebra ZPL — not Datamax/SATO. Confirm Emmanuel's printer brand |
| `adapters/chargeback_tracker.py` — dispute window | Tracks the timer | Relies on EDI 820 inbound parse — and we have no scheduler that polls for incoming 820s yet |
| `agents/email_agent.py` — IMAP polling | Works with username/password | Will break the day Office 365 forces OAuth-only on Emmanuel's tenant |
| `manager/orchestrator.py` — retry/escalate | 3-retry budget then escalate | Escalation = SMTP email; if SMTP is the thing that's broken, we lose the alert. Add a fallback (Telegram bridge per the meeting notes) |

---

## I. The dependencies behind the agent's "skills"

For each skill in `skills/`, here's what has to be true on Emmanuel's machine:

| Skill | Real dependency |
|-------|-----------------|
| PO parsing | Ollama running + model pulled, OR cloud LLM key set |
| A2000 entry | A2000 desktop app installed AND recipe recorded AND `HERMES_DESKTOP_AUTOMATION_ARMED=1` |
| Invoice email | SMTP credentials in `.env` AND outbound port open in his firewall |
| Carton labels | Zebra-compatible thermal printer + driver installed + `LABEL_PRINTER_NAME` matching the OS-level name (use `python scripts/printer_tool.py --list`) |
| Warehouse PO print | Standard printer + `WAREHOUSE_PRINTER_NAME` set |
| Folder watcher | Drop folder exists and Hermes has read access (`HERMES_PO_DROP_FOLDER`) |
| Daily briefing | All of the above generating audit-log entries |
| Chargeback dispute | EDI 820 inbound (we don't have an inbound poller yet — TODO) |

---

## J. The single highest-risk failure mode (read this twice)

**A wrong-customer order goes through.** Every other failure mode (a typo, a
missed field, a late ASN) is recoverable. A wrong-customer order is a financial
event you can't take back: the inventory is committed, the invoice is sent, and
recovery requires a human apology.

The defense is layered:

1. The PO parser must extract customer name from the *bill-to* / *sold-to*
   block, not the ship-to (already in the prompt).
2. The orchestrator must look up the customer in `storage` *before* entering
   the order, fail-stop on no match.
3. The desktop adapter's first `verify` step **must** confirm Emmanuel's chosen
   customer ID appears on the A2000 screen before any data is typed.
4. During week 1–2 of the trial, every order pauses for human review.

If we slip on any of these four, we're one bad day from losing trust. They are
not optional.

---

*Last reviewed: 2026-04-27. Next review: before Emmanuel's setup call.*
