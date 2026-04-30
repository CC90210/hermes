# install.ps1 — Hermes one-shot installer for Windows
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
# Requires: Python 3.12+, Git (checks both and errors if missing)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$RuntimeDirs = @(
    "storage",
    "storage\a2000_screenshots",
    "logs",
    "drafts",
    "tmp"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hermes — Commerce Agent Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------
# STEP 1 — Check Python 3.12+
# -----------------------------------------------------------------------
Write-Host "[1/9] Checking Python..." -ForegroundColor Yellow
$pythonCmd = $null
foreach ($cmd in @("python3.12", "python3", "python")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 12) {
                $pythonCmd = $cmd
                Write-Host "  Python $ver found." -ForegroundColor Green
                break
            }
        }
    } catch { }
}
if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3.12 or higher is required." -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# STEP 2 — Check Git
# -----------------------------------------------------------------------
Write-Host "[2/9] Checking Git..." -ForegroundColor Yellow
try {
    $gitVer = & git --version 2>&1
    Write-Host "  $gitVer found." -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Git is required." -ForegroundColor Red
    Write-Host "  Download from: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# STEP 3 — Create virtualenv and install requirements
# -----------------------------------------------------------------------
Write-Host "[3/9] Creating virtual environment..." -ForegroundColor Yellow
Write-Host "  Preparing runtime folders..." -ForegroundColor Yellow
foreach ($dir in $RuntimeDirs) {
    $path = Join-Path $RepoRoot $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}
Write-Host "  Runtime folders ready." -ForegroundColor Green

$venvPath = Join-Path $RepoRoot ".venv"
if (-not (Test-Path $venvPath)) {
    & $pythonCmd -m venv $venvPath
    Write-Host "  .venv created." -ForegroundColor Green
} else {
    Write-Host "  .venv already exists — skipping." -ForegroundColor DarkGray
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
$python = Join-Path $venvPath "Scripts\python.exe"
$reqFile = Join-Path $RepoRoot "requirements.txt"

Write-Host "  Installing requirements (this may take a minute)..." -ForegroundColor Yellow
& $pip install -r $reqFile --quiet
Write-Host "  Requirements installed." -ForegroundColor Green

# -----------------------------------------------------------------------
# STEP 4 — Check Ollama
# -----------------------------------------------------------------------
Write-Host "[4/9] Checking Ollama..." -ForegroundColor Yellow
$ollamaOk = $false
try {
    $ollamaCheck = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  Ollama is running." -ForegroundColor Green
    $ollamaOk = $true
} catch {
    Write-Host "  Ollama not detected." -ForegroundColor DarkYellow
    Write-Host "  Install from: https://ollama.com/download" -ForegroundColor Yellow
    Write-Host "  After installing, run: ollama pull qwen2.5:32b (or qwen2.5:7b for lower RAM)" -ForegroundColor Yellow
    Write-Host "  Then re-run this installer." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# STEP 5 — Pull qwen2.5:32b if Ollama is running and RAM allows
# -----------------------------------------------------------------------
if ($ollamaOk) {
    Write-Host "[5/9] Checking available RAM for model pull..." -ForegroundColor Yellow
    $ram = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB
    Write-Host "  Detected RAM: $([math]::Round($ram, 1)) GB" -ForegroundColor DarkGray
    if ($ram -ge 20) {
        Write-Host "  Pulling qwen2.5:32b (large model — may take 10-20 min on first run)..." -ForegroundColor Yellow
        & ollama pull qwen2.5:32b
        Write-Host "  Model ready." -ForegroundColor Green
    } else {
        Write-Host "  RAM < 20GB — pulling qwen2.5:7b (lighter model)..." -ForegroundColor Yellow
        & ollama pull qwen2.5:7b
        Write-Host "  Lighter model ready. Set OLLAMA_MODEL=qwen2.5:7b in .env if needed." -ForegroundColor Green
    }
} else {
    Write-Host "[5/9] Skipping model pull (Ollama not running)." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------
# STEP 6 — Check Claude Code
# -----------------------------------------------------------------------
Write-Host "[6/9] Checking Claude Code..." -ForegroundColor Yellow
$claudeOk = $false
try {
    $claudeVer = & claude --version 2>&1
    Write-Host "  Claude Code found: $claudeVer" -ForegroundColor Green
    $claudeOk = $true
} catch {
    Write-Host "  Claude Code not found." -ForegroundColor DarkYellow
    Write-Host "  Download from: https://claude.ai/download" -ForegroundColor Yellow
    Write-Host "  (You can continue setup and install it later)" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# STEP 7 — Copy .env template
# -----------------------------------------------------------------------
Write-Host "[7/9] Setting up .env file..." -ForegroundColor Yellow
$envFile = Join-Path $RepoRoot ".env"
$templateFile = Join-Path $RepoRoot ".env.template"

if (-not (Test-Path $envFile)) {
    if (Test-Path $templateFile) {
        Copy-Item $templateFile $envFile
        Write-Host "  .env created from template." -ForegroundColor Green
    } else {
        # Create a minimal template if client template not found
        $defaultEnv = @"
# Hermes environment — Lowinger Distribution
# Fill in all values before starting the pipeline

# Database
DB_PATH=storage/lowinger.db

# Email (Outlook / Microsoft 365)
EMAIL_IMAP_HOST=outlook.office365.com
EMAIL_SMTP_HOST=smtp.office365.com
EMAIL_SMTP_PORT=587
EMAIL_USER=your_email@lowinderdistribution.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_FROM=your_email@lowinderdistribution.com

# Escalation recipient
ESCALATION_EMAIL=emmanuel@lowinderdistribution.com

# A2000 mode: mock | edi | api | playwright | desktop
A2000_MODE=mock
EDI_OUTPUT_DIR=C:\A2000\EDI\incoming

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:32b

# Health endpoint port
HEALTH_PORT=8765
"@
        $defaultEnv | Out-File -FilePath $envFile -Encoding UTF8
        Write-Host "  .env created with defaults." -ForegroundColor Green
    }
    Write-Host "  Opening .env in Notepad — fill in your credentials, then save and close." -ForegroundColor Cyan
    Start-Process notepad.exe -ArgumentList $envFile -Wait
} else {
    Write-Host "  .env already exists — skipping." -ForegroundColor DarkGray
}

# -----------------------------------------------------------------------
# STEP 8 — Initialize the database
# -----------------------------------------------------------------------
Write-Host "[8/9] Initializing database..." -ForegroundColor Yellow
try {
    & $python (Join-Path $RepoRoot "scripts\setup_db.py")
    Write-Host "  Database ready." -ForegroundColor Green
} catch {
    Write-Host "  ERROR initializing database: $_" -ForegroundColor Red
    exit 1
}

# -----------------------------------------------------------------------
# STEP 9 — Run demo to verify
# -----------------------------------------------------------------------
Write-Host "[9/9] Running verification demo..." -ForegroundColor Yellow
try {
    & $python -m demo.run_demo 2>&1 | Select-Object -Last 5
    Write-Host "  Demo passed." -ForegroundColor Green
} catch {
    Write-Host "  Demo failed: $_" -ForegroundColor Red
    Write-Host "  Check .env values and retry. Pipeline will not start until demo passes." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# DONE
# -----------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Hermes installation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Open Claude Code" -ForegroundColor White
Write-Host "  2. Open this folder: $RepoRoot" -ForegroundColor White
Write-Host "  3. Start talking to Hermes — just type naturally." -ForegroundColor White
Write-Host ""
Write-Host "To start the background pipeline:" -ForegroundColor Cyan
Write-Host "  .venv\Scripts\python.exe main.py" -ForegroundColor White
Write-Host ""
Write-Host "Quick commands in Claude Code:" -ForegroundColor Cyan
Write-Host "  /daily-briefing  /status  /chargebacks  /quote <customer>" -ForegroundColor White
Write-Host ""
