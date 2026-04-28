from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

A2000Mode = Literal["mock", "api", "edi", "playwright", "desktop"]

# EMAIL_USER / EMAIL_PASSWORD are required at runtime when EmailAgent connects,
# but NOT at import time. Importing this module with a missing .env (e.g. from a
# fresh checkout, a CLI script, or a unit test) must not crash — otherwise every
# tool crashes with a confusing import error instead of the actionable message
# from the agent that actually needs the credential.
_REQUIRED_AT_RUNTIME: list[str] = [
    "EMAIL_USER",
    "EMAIL_PASSWORD",
]


def require_email_credentials() -> tuple[str, str]:
    """Return (user, password) or raise EnvironmentError with a clear message.

    Call this from EmailAgent.connect — not at import time.
    """
    missing = [v for v in _REQUIRED_AT_RUNTIME if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Hermes: missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.template to .env and fill in all required values."
        )
    return os.environ["EMAIL_USER"], os.environ["EMAIL_PASSWORD"]


@dataclass(frozen=True)
class Config:
    # Ollama
    ollama_host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen2.5:32b"))

    # Email — IMAP (inbound PO polling)
    # Returns "" when not set; require_email_credentials() enforces presence at runtime.
    email_host: str = field(default_factory=lambda: os.environ.get("EMAIL_HOST", "outlook.office365.com"))
    email_user: str = field(default_factory=lambda: os.environ.get("EMAIL_USER", ""))
    email_password: str = field(default_factory=lambda: os.environ.get("EMAIL_PASSWORD", ""))
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

    # Company info
    company_name: str = field(
        default_factory=lambda: os.environ.get("COMPANY_NAME", "Lowinger")
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


def _validate_config(cfg: "Config") -> None:
    """Validate cross-field config constraints after construction.

    This is a soft check at import time — issues a warning so tests and
    dev shells can import the module without a full .env. Hard validation
    of ESCALATION_EMAIL happens inside escalate() when it would actually
    be used.
    """
    import logging
    log = logging.getLogger(__name__)
    if not cfg.escalation_email:
        log.warning(
            "ESCALATION_EMAIL is not set — Hermes will not be able to send "
            "alerts when orders fail. Set it in .env before deploying to production."
        )


def require_escalation_email() -> str:
    """Return the configured escalation email or raise if missing.

    Call this from code paths that actually need to send an escalation
    (e.g. Orchestrator.escalate). Import-time code should not call this.
    """
    if not config.escalation_email:
        raise EnvironmentError(
            "ESCALATION_EMAIL is required for this operation — set it in .env. "
            "Hermes sends alerts to this address when orders fail after retries."
        )
    return config.escalation_email


def _validated_a2000_mode(value: str) -> A2000Mode:
    allowed: tuple[A2000Mode, ...] = ("mock", "api", "edi", "playwright", "desktop")
    if value not in allowed:
        raise ValueError(
            f"A2000_MODE must be one of {allowed}, got '{value}'"
        )
    # Validate mode-specific required variables
    if value == "api":
        for key in ("A2000_API_URL", "A2000_API_KEY"):
            if not os.getenv(key):
                raise EnvironmentError(
                    f"A2000_MODE=api requires {key} to be set in the environment."
                )
    elif value == "edi":
        for key in ("EDI_OUTPUT_DIR", "EDI_SENDER_ID", "EDI_RECEIVER_ID"):
            if not os.getenv(key):
                raise EnvironmentError(
                    f"A2000_MODE=edi requires {key} to be set in the environment."
                )
    elif value == "desktop":
        for key in ("A2000_EXECUTABLE_PATH", "A2000_WINDOW_TITLE"):
            if not os.getenv(key):
                raise EnvironmentError(
                    f"A2000_MODE=desktop requires {key} to be set in the environment."
                )
    return value  # type: ignore[return-value]


# Module-level singleton — import this everywhere rather than constructing repeatedly.
config = Config()
_validate_config(config)
