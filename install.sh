#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say() { printf '%s\n' "$*"; }
ok() { printf '  OK: %s\n' "$*"; }
warn() { printf '  WARN: %s\n' "$*"; }
fail() { printf '  ERROR: %s\n' "$*" >&2; exit 1; }

say ""
say "========================================"
say "  Hermes - Commerce Agent Installer"
say "========================================"
say ""

PYTHON_CMD=""
for cmd in python3.12 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
        then
            PYTHON_CMD="$cmd"
            ok "$($cmd --version)"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.12+ is required. Install it from https://www.python.org/downloads/ and re-run this script."
fi

command -v git >/dev/null 2>&1 || fail "Git is required. Install it from https://git-scm.com/downloads and re-run."
ok "$(git --version)"

say "[1/7] Preparing runtime folders..."
mkdir -p "$REPO_ROOT/storage/a2000_screenshots" "$REPO_ROOT/logs" "$REPO_ROOT/drafts" "$REPO_ROOT/tmp"
ok "runtime folders ready"

say "[2/7] Creating virtual environment..."
if [ ! -d "$REPO_ROOT/.venv" ]; then
    "$PYTHON_CMD" -m venv "$REPO_ROOT/.venv"
    ok ".venv created"
else
    ok ".venv already exists"
fi

PY="$REPO_ROOT/.venv/bin/python"
PIP="$REPO_ROOT/.venv/bin/pip"

say "[3/7] Installing Python requirements..."
"$PIP" install -r "$REPO_ROOT/requirements.txt" --quiet
ok "requirements installed"

say "[4/7] Checking Ollama..."
if command -v curl >/dev/null 2>&1 && curl -fsS --max-time 5 "http://localhost:11434/api/tags" >/dev/null 2>&1; then
    ok "Ollama is running"
    if command -v ollama >/dev/null 2>&1; then
        RAM_GB="$("$PYTHON_CMD" - <<'PY'
import os, sys
if sys.platform == "darwin":
    import subprocess
    print(round(int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 1024**3, 1))
else:
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            kb = int(next(line for line in fh if line.startswith("MemTotal:")).split()[1])
        print(round(kb / 1024**2, 1))
    except Exception:
        print(0)
PY
)"
        MODEL="qwen2.5:7b"
        "$PYTHON_CMD" - <<PY && MODEL="qwen2.5:32b" || true
import sys
raise SystemExit(0 if float("$RAM_GB") >= 20 else 1)
PY
        say "  Pulling $MODEL if missing..."
        ollama pull "$MODEL"
        ok "model ready"
    else
        warn "Ollama service is reachable, but the ollama CLI is not on PATH"
    fi
else
    warn "Ollama is not running. Install from https://ollama.com/download, then pull qwen2.5:32b or qwen2.5:7b."
fi

say "[5/7] Checking Claude Code..."
if command -v claude >/dev/null 2>&1; then
    ok "Claude Code found: $(claude --version 2>&1 | head -n 1)"
else
    warn "Claude Code not found. Install it later from https://claude.ai/download."
fi

say "[6/7] Setting up .env..."
if [ ! -f "$REPO_ROOT/.env" ]; then
    cp "$REPO_ROOT/.env.template" "$REPO_ROOT/.env"
    ok ".env created from .env.template"
    if command -v open >/dev/null 2>&1; then
        open -t "$REPO_ROOT/.env" >/dev/null 2>&1 || true
    fi
else
    ok ".env already exists"
fi

say "[7/7] Initializing database and running demo..."
"$PY" "$REPO_ROOT/scripts/setup_db.py"
"$PY" -m demo.run_demo >/tmp/hermes_demo.out
tail -n 5 /tmp/hermes_demo.out || true
ok "demo passed"

say ""
say "========================================"
say "  Hermes installation complete"
say "========================================"
say ""
say "Next:"
say "  1. Open Claude Code."
say "  2. Open this folder: $REPO_ROOT"
say "  3. Run: $PY main.py --once"
say ""
