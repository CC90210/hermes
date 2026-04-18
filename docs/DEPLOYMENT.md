# Hermes — Deployment Guide

This guide covers installing Hermes on Emmanuel's Windows machine from
scratch through to a running, auto-starting service.

---

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 (64-bit) | Windows 11 |
| RAM | 16 GB | 32 GB |
| Disk | 50 GB free | 100 GB free |
| CPU | 8-core (Intel/AMD) | 12-core+ |
| GPU | None (CPU inference) | NVIDIA with 8 GB VRAM |
| Python | 3.12 | 3.12 |
| Internet | Required for initial setup | Broadband |

> The qwen2.5:32b Ollama model is approximately 20 GB. Ensure the target drive
> has at least 50 GB free before beginning.

---

## Step-by-Step Installation

### 1. Clone the repository

Open PowerShell or Git Bash:

```powershell
cd C:\Users\Emmanuel\Documents
git clone https://github.com/CC90210/hermes.git
cd hermes
```

If Git is not installed, download from https://git-scm.com/download/win and
run the installer with default settings.

### 2. Install Python 3.12

1. Download from https://www.python.org/downloads/release/python-3120/
2. Run the installer.
3. **Check "Add python.exe to PATH"** on the first screen.
4. Choose "Install Now".
5. Verify: open a new PowerShell window and run:

```powershell
python --version
# Expected: Python 3.12.x
```

### 3. Create a virtual environment and install dependencies

```powershell
cd C:\Users\Emmanuel\Documents\hermes
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Ollama

1. Download from https://ollama.com/download/windows
2. Run the installer (OllamaSetup.exe).
3. After installation, open a new PowerShell window and pull the model:

```powershell
ollama pull qwen2.5:32b
```

This downloads ~20 GB and may take 20–60 minutes depending on connection speed.
Once complete, verify:

```powershell
ollama list
# Should show: qwen2.5:32b
```

Ollama runs as a background service automatically after installation.
It listens on `http://localhost:11434` by default.

### 5. Configure the environment file

```powershell
cd C:\Users\Emmanuel\Documents\hermes
copy .env.template .env
notepad .env
```

Fill in the required values (see "Configuring credentials" sections below).
Save and close Notepad.

### 6. Verify the installation

Run a single cycle in health-check mode:

```powershell
.venv\Scripts\activate
python main.py --health
```

Expected output (with `A2000_MODE=mock` and valid email credentials):

```json
{
  "email_connected": true,
  "a2000_reachable": true,
  "pending_orders": 0,
  "failed_orders": 0,
  "cycle_count": 0,
  "timestamp": "2026-04-16T..."
}
```

If `email_connected` is `false`, see the Troubleshooting section.

### 7. Start the agent

Double-click `start.bat` in the project folder, or from PowerShell:

```powershell
.venv\Scripts\activate
python main.py
```

The agent will run continuously, polling every 5 minutes (300 seconds).
Log output goes to the `logs/` directory and stdout.

---

## Configuring Outlook IMAP/SMTP Credentials

### Enable IMAP in Outlook 365

1. Log in to https://outlook.office.com
2. Go to Settings (gear icon) → View all Outlook settings
3. Mail → Sync email
4. Under "POP and IMAP", enable IMAP.
5. Click Save.

### App password (if MFA is enabled)

If Emmanuel's account uses multi-factor authentication, an app-specific
password is required. Standard passwords will not work.

1. Go to https://mysignins.microsoft.com/security-info
2. Click "Add method" → App password
3. Name it "Hermes" and copy the generated password.
4. Paste into `EMAIL_PASSWORD` in `.env`.

### `.env` values

```dotenv
EMAIL_HOST=outlook.office365.com
EMAIL_USER=orders@lowinger.com        # the monitored inbox
EMAIL_PASSWORD=<app password here>
EMAIL_IMAP_PORT=993

EMAIL_SMTP_HOST=smtp.office365.com
EMAIL_SMTP_PORT=587
```

---

## Configuring A2000 Connection

### Current state

`A2000_MODE` defaults to `mock`. The system is fully functional in this mode
for testing and demo — it generates fake order IDs and stub invoice PDFs
without touching the real POS.

### When A2000 API access is granted

Once the A2000 vendor provides API credentials:

1. Set in `.env`:
   ```dotenv
   A2000_MODE=api
   A2000_API_URL=https://api.a2000.example.com/v1
   A2000_API_KEY=<key from vendor>
   ```
2. Implement the method bodies in `adapters/a2000_api.py` using the vendor's
   API documentation (the stubs raise `NotImplementedError` until then).

### EDI mode (AS2/VAN)

If the integration uses EDI 850 documents over AS2 or a VAN:

```dotenv
A2000_MODE=edi
EDI_OUTPUT_DIR=C:\Lowinger\edi_out
EDI_SENDER_ID=LOWINGER
EDI_RECEIVER_ID=A2000
```

The agent will write X12 850 files to `EDI_OUTPUT_DIR`. The AS2 client or VAN
client picks them up from that folder on its own schedule.

### Playwright mode (screen automation)

Use this only as a last resort if no API or EDI integration is available.
Requires recording the A2000 order-entry screen flow and implementing the
selectors in `adapters/a2000_playwright.py`.

---

## Auto-Start on Boot (Task Scheduler)

This configures the agent to start automatically when Windows starts, without
requiring anyone to log in.

1. Open Task Scheduler (search "Task Scheduler" in Start menu).
2. Click "Create Task" (not "Create Basic Task").
3. **General tab:**
   - Name: `Hermes`
   - Description: `Automated purchase order processing agent`
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
   - Configure for: Windows 10 (or Windows 11)
4. **Triggers tab:** Click New
   - Begin the task: At startup
   - Delay task for: 2 minutes (allows network to come up)
   - Click OK
5. **Actions tab:** Click New
   - Action: Start a program
   - Program/script: `C:\Users\Emmanuel\Documents\hermes\start.bat`
   - Start in: `C:\Users\Emmanuel\Documents\hermes`
   - Click OK
6. **Conditions tab:**
   - Uncheck "Start the task only if the computer is on AC power" (if this
     is a desktop, leave it; if a laptop, uncheck it)
7. **Settings tab:**
   - Check "If the task is already running, do not start a new instance"
8. Click OK. Enter Windows credentials when prompted.

To verify: restart the machine and check that a `hermes.log` file
appears in the `logs/` directory within a few minutes.

---

## Backup Strategy

### What to back up

| Item | Why | Frequency |
|------|-----|-----------|
| `.env` | Contains all credentials | Every time credentials change |
| `storage/lowinger.db` | All order history and audit log | Daily |
| `storage/edi_out/` | EDI files (if using EDI mode) | Daily |

### Recommended approach

1. Copy the `hermes` folder to an external drive or network share weekly.
2. For the database alone (lighter, faster):
   ```powershell
   # Run from PowerShell — safe to run while agent is active (WAL mode)
   copy storage\lowinger.db storage\lowinger.db.bak
   ```
3. For automated daily backup, add a second Scheduled Task that runs:
   ```powershell
   xcopy /Y C:\Users\Emmanuel\Documents\hermes\storage\lowinger.db ^
         D:\Backups\hermes\hermes_%DATE%.db
   ```

---

## Troubleshooting

### `email_connected: false` in health check

- Verify `EMAIL_USER` and `EMAIL_PASSWORD` are correct in `.env`.
- If MFA is enabled, confirm an app password is being used (not the account
  password).
- Test manually:
  ```powershell
  python -c "
  import imapclient, os
  from dotenv import load_dotenv
  load_dotenv()
  c = imapclient.IMAPClient('outlook.office365.com', port=993, ssl=True)
  c.login(os.environ['EMAIL_USER'], os.environ['EMAIL_PASSWORD'])
  print('Login OK')
  c.logout()
  "
  ```

### `a2000_reachable: false` in health check

- In `mock` mode this should always be `true`. If it is `false`, a Python
  exception occurred during adapter initialisation — check the `logs/` directory.
- In `api` mode: verify `A2000_API_URL` and `A2000_API_KEY` are set and the
  A2000 server is reachable from this machine.

### Ollama not responding

- Open Services (Win+R → `services.msc`) and confirm "Ollama" is running.
- Or restart from PowerShell: `ollama serve`
- Verify the model is downloaded: `ollama list`
- If the model was deleted, re-pull: `ollama pull qwen2.5:32b`

### Agent crashes on startup with `EnvironmentError`

The config module requires `EMAIL_USER` and `EMAIL_PASSWORD`. Confirm `.env`
exists in the project root and both values are non-empty.

### Orders stuck in FAILED status

Query the audit log:
```sql
-- Run in any SQLite browser, e.g. DB Browser for SQLite
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 50;
```

Common causes:
- A2000 rejected the order (check `details_json` for the error message).
- Invoice PDF not available yet — the agent will retry automatically.
- Email delivery failed — check SMTP credentials and Outlook sending limits.

### Log files growing too large

Log rotation is not built in. Add a scheduled task to archive old logs weekly,
or set `LOG_LEVEL=WARNING` in `.env` to reduce verbosity.
