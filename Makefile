.DEFAULT_GOAL := help
PYTHON        := .venv/Scripts/python
PIP           := .venv/Scripts/pip
PYTEST        := .venv/Scripts/pytest
RUFF          := .venv/Scripts/ruff

# Detect OS: use unix-style paths unless on Windows outside WSL
ifeq ($(OS),Windows_NT)
  VENV_PYTHON := .venv/Scripts/python.exe
  VENV_PIP    := .venv/Scripts/pip.exe
  PYTEST      := .venv/Scripts/pytest.exe
  RUFF        := .venv/Scripts/ruff.exe
else
  VENV_PYTHON := .venv/bin/python
  VENV_PIP    := .venv/bin/pip
  PYTEST      := .venv/bin/pytest
  RUFF        := .venv/bin/ruff
endif

.PHONY: help install test lint format demo run health clean

help:
	@echo ""
	@echo "Hermes — make targets"
	@echo "----------------------------"
	@echo "  install   Create .venv and install all dependencies"
	@echo "  test      Run pytest test suite"
	@echo "  lint      Run ruff linter"
	@echo "  format    Run ruff formatter"
	@echo "  demo      Run demo/run_demo.py (mock mode, no external deps)"
	@echo "  run       Start the agent (reads .env)"
	@echo "  health    Print subsystem health as JSON and exit"
	@echo "  clean     Remove __pycache__, .pytest_cache, and *.pyc files"
	@echo ""

install:
	python -m venv .venv
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install ruff pre-commit
	@echo "Virtual environment ready. Activate with: .venv\\Scripts\\activate (Windows) or source .venv/bin/activate (Unix)"

test:
	$(PYTEST) tests/ -v

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

demo:
	$(VENV_PYTHON) demo/run_demo.py

run:
	$(VENV_PYTHON) main.py

health:
	$(VENV_PYTHON) main.py --health

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "Clean complete."
