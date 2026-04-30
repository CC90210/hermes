from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[1]


def load_env(repo_root: Path | None = None) -> None:
    """Load Hermes environment files in setup-wizard compatible order.

    The OASIS setup wizard writes answers to `.env.agents`; the legacy Hermes
    installer still writes `.env`. Load `.env.agents` first so wizard answers
    win over untouched template defaults, then let `.env` fill any missing
    deployment-specific values.
    """
    root = repo_root or _REPO_ROOT
    load_dotenv(root / ".env.agents")
    load_dotenv(root / ".env")
