"""health_tool.py — Hermes pipeline health check CLI.

Usage:
    python scripts/health_tool.py
    python scripts/health_tool.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

load_dotenv(_REPO_ROOT / ".env")

import aiosqlite  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", str(_REPO_ROOT / "storage" / "lowinger.db")))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8765"))


async def _db_health() -> dict:
    if not DB_PATH.exists():
        return {"status": "error", "message": "DB file not found", "path": str(DB_PATH)}
    try:
        size_kb = DB_PATH.stat().st_size // 1024
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM orders") as cur:
                count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM audit_log") as cur:
                audit_count = (await cur.fetchone())[0]
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            async with db.execute(
                "SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?", (cutoff,)
            ) as cur:
                recent_activity = (await cur.fetchone())[0]
        return {
            "status": "ok",
            "total_orders": count,
            "audit_entries": audit_count,
            "recent_activity_1h": recent_activity,
            "size_kb": size_kb,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _ollama_health() -> dict:
    import httpx
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"status": "ok", "models": models, "host": OLLAMA_HOST}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "host": OLLAMA_HOST}


def _pipeline_health() -> dict:
    """Check if the background pipeline process was recently active via audit log."""
    return {"status": "check_db", "note": "Check recent_activity_1h in db health for pipeline liveness"}


def _hermes_health_endpoint() -> dict:
    """Try the FastAPI health endpoint if main.py is running."""
    import httpx
    try:
        resp = httpx.get(f"http://localhost:{HEALTH_PORT}/health", timeout=3.0)
        return {"status": "ok", "data": resp.json()}
    except Exception:
        return {"status": "not_running", "note": "main.py health endpoint not reachable — background pipeline may not be running"}


async def full_health() -> dict:
    db = await _db_health()
    ollama = _ollama_health()
    endpoint = _hermes_health_endpoint()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": db,
        "ollama": ollama,
        "pipeline_endpoint": endpoint,
        "overall": "ok" if db["status"] == "ok" else "degraded",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes health tool")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    data = asyncio.run(full_health())

    if args.as_json:
        print(json.dumps(data, indent=2))
        return

    print(f"=== Hermes Health [{data['overall'].upper()}] ===")
    db = data["db"]
    if db["status"] == "ok":
        print(f"  DB:      OK ({db['total_orders']} orders, {db['size_kb']}KB, {db['recent_activity_1h']} audit entries last 1h)")
    else:
        print(f"  DB:      ERROR — {db.get('message', '')}")

    ollama = data["ollama"]
    if ollama["status"] == "ok":
        print(f"  Ollama:  OK — models: {', '.join(ollama['models'][:3])}")
    else:
        print(f"  Ollama:  ERROR — {ollama.get('message', '')} (host: {ollama['host']})")

    ep = data["pipeline_endpoint"]
    if ep["status"] == "ok":
        print("  Pipeline endpoint: OK")
    else:
        print(f"  Pipeline endpoint: {ep['note']}")


if __name__ == "__main__":
    main()
