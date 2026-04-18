"""
cron/scheduler.py
-----------------
CLI entry point for the Hermes scheduler.

Usage:
    python -m cron.scheduler                     # run forever (default 300s interval)
    python -m cron.scheduler --interval 60       # run forever, 60s between cycles
    python -m cron.scheduler --once              # single cycle then exit
    python -m cron.scheduler --health            # print health check and exit
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from manager.config import config  # noqa: E402


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    log_dir: Path = config.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "aos.log", encoding="utf-8"),
    ]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=handlers,
    )


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Async runners
# ---------------------------------------------------------------------------

async def _run_once() -> None:
    from manager.orchestrator import Orchestrator

    orch = Orchestrator()
    await orch.setup()
    summary = await orch.run_cycle()
    await orch.handle_failures()
    logger.info("Single-cycle complete: %s", summary)


async def _run_health() -> None:
    from manager.orchestrator import Orchestrator

    orch = Orchestrator()
    await orch.setup()
    health = await orch.health_check()
    print(json.dumps(health, indent=2))


async def _run_forever(interval: int) -> None:
    from manager.orchestrator import Orchestrator

    orch = Orchestrator()
    await orch.setup()
    await orch.run_forever(interval_seconds=interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cron.scheduler",
        description="Hermes — automated order scheduler",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Run a single automation cycle then exit.",
    )
    mode_group.add_argument(
        "--health",
        action="store_true",
        help="Print subsystem health status as JSON and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Seconds between automation cycles (default: 300).",
    )
    return parser


def main() -> None:
    _configure_logging()
    args = _build_parser().parse_args()

    logger.info(
        "Hermes scheduler starting — mode=%s, model=%s, email=%s",
        config.a2000_mode,
        config.ollama_model,
        config.email_user,
    )

    try:
        if args.health:
            asyncio.run(_run_health())
        elif args.once:
            logger.info("Running single cycle (--once).")
            asyncio.run(_run_once())
        else:
            logger.info("Running forever with interval=%ds.", args.interval)
            asyncio.run(_run_forever(args.interval))
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — scheduler stopped.")
    except Exception:
        logger.exception("Fatal error in scheduler.")
        sys.exit(1)


if __name__ == "__main__":
    main()
