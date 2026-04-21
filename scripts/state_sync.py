"""state_sync.py — Hermes session-end sync.

Updates memory/STATE.md, memory/SESSION_LOG.md, and memory/ACTIVE_TASKS.md.
Run at the end of every IDE session (non-negotiable per CLAUDE.md Rule 5).

Usage:
    python scripts/state_sync.py --note "Drafted Walgreens Q3 quote, pending approval"
    python scripts/state_sync.py --note "Fixed failed order 42, re-queued for processing"
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))
MEMORY_DIR = _REPO_ROOT / "memory"
MEMORY_DIR.mkdir(exist_ok=True)


async def _get_pipeline_stats() -> dict:
    if not DB_PATH.exists():
        return {"total_orders": 0, "failed_orders": 0, "pending_orders": 0}
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders") as cur:
            total = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status = 'failed'") as cur:
            failed = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE status IN ('received','parsing','parsed','entering','entered')"
        ) as cur:
            pending = (await cur.fetchone())[0]
    return {"total_orders": total, "failed_orders": failed, "pending_orders": pending}


def _update_state_md(note: str, stats: dict) -> None:
    state_path = MEMORY_DIR / "STATE.md"
    now = datetime.now(timezone.utc).isoformat()
    content = f"""---
tags: [hermes, state, ephemeral]
last_synced: {now}
---

# Hermes — Operational State

> Ephemeral. Overwritten at each session end. Read at session start.

## Last Session Note
{note}

## Pipeline Stats (at sync time)
- Total orders in DB: {stats['total_orders']}
- Failed orders:      {stats['failed_orders']}
- Pending orders:     {stats['pending_orders']}

## Sync timestamp
{now}
"""
    state_path.write_text(content, encoding="utf-8")


def _append_session_log(note: str) -> None:
    log_path = MEMORY_DIR / "SESSION_LOG.md"
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M UTC")
    line = f"\n### {date_str}\n{note}\n"
    if not log_path.exists():
        log_path.write_text(
            "---\ntags: [hermes, memory, session-log]\n---\n\n# Hermes — Session Log\n\n> Append-only. One entry per session.\n",
            encoding="utf-8",
        )
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)


def _ensure_active_tasks() -> None:
    tasks_path = MEMORY_DIR / "ACTIVE_TASKS.md"
    if not tasks_path.exists():
        tasks_path.write_text(
            "---\ntags: [hermes, memory, tasks]\n---\n\n# Hermes — Active Tasks\n\n> Updated after every material action.\n\n## Open\n_None yet._\n\n## Blocked\n_None yet._\n\n## Done\n_None yet._\n",
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes state sync (run at session end)")
    parser.add_argument("--note", required=True, help="One-sentence summary of this session")
    args = parser.parse_args()

    stats = asyncio.run(_get_pipeline_stats())
    _update_state_md(args.note, stats)
    _append_session_log(args.note)
    _ensure_active_tasks()

    print(f"Memory synced. STATE.md updated. Session log appended.")
    print(f"Stats: {stats['total_orders']} total orders, {stats['failed_orders']} failed, {stats['pending_orders']} pending.")


if __name__ == "__main__":
    main()
