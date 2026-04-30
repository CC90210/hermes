"""
main.py
-------
Top-level entry point for Hermes — The Commerce Agent.

Usage:
    python main.py               # run forever (300s interval)
    python main.py --once        # single cycle then exit
    python main.py --health      # print health status as JSON and exit
    python main.py --interval N  # run forever with N-second interval
"""

from __future__ import annotations

import sys

from runtime.env_loader import load_env

load_env()

from manager.config import config  # noqa: E402

_VERSION = "0.1.0"


def _print_banner() -> None:
    lines = [
        "",
        "╔══════════════════════════════════════════╗",
        f"║  HERMES  v{_VERSION:<31}║",
        f'║  "Your commerce agent"                  ║',
        f"║  Mode   : {config.a2000_mode:<32}║",
        f"║  Model  : {config.ollama_model:<32}║",
        f"║  Email  : {config.email_user:<32}║",
        "╚══════════════════════════════════════════╝",
        "",
    ]
    for line in lines:
        print(line)


def main() -> None:
    # Delegate all argument parsing and async execution to cron.scheduler,
    # which already implements the full CLI.  main.py is a thin launcher that
    # adds the startup banner and re-exports the entry point.
    _print_banner()

    from cron.scheduler import main as scheduler_main
    scheduler_main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
