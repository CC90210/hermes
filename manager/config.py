from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

A2000Mode = Literal["mock", "api", "edi", "playwright"]

_REQUIRED: list[str] = [
    "EMAIL_USER",
    "EMAIL_PASSWORD",
]

_MISSING = [v for v in _REQUIRED if not os.getenv(v)]
if _MISSING:
    raise EnvironmentError(
        f"Hermes: missing required environment variables: {', '.join(_MISSING)}\n"
        "Copy .env.template to .env and fill in all required values."
    )


@dataclass(frozen=True)
class Config:
    # Ollama
    ollama_host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen2.5:32b"))

    # Email — IMAP (inbound PO polling)
    email_host: str = field(default_factory=lambda: os.environ.get("EMAIL_HOST", "outlook.office365.com"))
    email_user: str = field(default_factory=lambda: os.environ["EMAIL_USER"])
    email_password: str = field(default_factory=lambda: os.environ["EMAIL_PASSWORD"])
    email_imap_port: int = field(default_factory=lambda: int(os.environ.get("EMAIL_IMAP_PORT", "993")))

    # Email — SMTP (outbound invoices / confirmations)
    email_smtp_host: str = field(default_factory=lambda: os.environ.get("EMAIL_SMTP_HOST", "smtp.office365.com"))
    email_smtp_port: int = field(default_factory=lambda: int(os.environ.get("EMAIL_SMTP_PORT", "587")))

    # A2000 POS integration
    a2000_api_url: str = field(default_factory=lambda: os.environ.get("A2000_API_URL", ""))
    a2000_api_key: str = field(default_factory=lambda: os.environ.get("A2000_API_KEY", ""))
    a2000_mode: A2000Mode = field(
        default_factory=lambda: _validated_a2000_mode(os.environ.get("A2000_MODE", "mock"))
    )

    # Storage
    db_path: Path = field(
        default_factory=lambda: Path(os.environ.get("DB_PATH", "./storage/lowinger.db"))
    )

    # Escalation
    escalation_email: str = field(
        default_factory=lambda: os.environ.get("ESCALATION_EMAIL", "")
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    log_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("LOG_DIR", "./logs"))
    )


def _validated_a2000_mode(value: str) -> A2000Mode:
    allowed: tuple[A2000Mode, ...] = ("mock", "api", "edi", "playwright")
    if value not in allowed:
        raise ValueError(
            f"A2000_MODE must be one of {allowed}, got '{value}'"
        )
    return value  # type: ignore[return-value]


# Module-level singleton — import this everywhere rather than constructing repeatedly.
config = Config()
