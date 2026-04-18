@echo off
echo Starting Hermes...
cd /d "%~dp0"
if not exist .venv (
    echo First-time setup: creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
python main.py
pause
