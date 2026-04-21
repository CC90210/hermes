"""setup_db.py — Initialize the Hermes SQLite database.

Run by install.ps1 and during first-time setup.

Usage:
    python scripts/setup_db.py
    python scripts/setup_db.py --db-path custom/path/hermes.db
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

from storage.db import init_db  # noqa: E402


async def setup(db_path: Path) -> None:
    print(f"Initializing Hermes database at: {db_path}")
    await init_db(db_path)
    print("Database initialized successfully.")
    print("Tables: orders, order_lines, audit_log, email_queue")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the Hermes SQLite database")
    parser.add_argument(
        "--db-path",
        default=os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")),
        help="Path to the SQLite database file",
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    asyncio.run(setup(db_path))


if __name__ == "__main__":
    main()
