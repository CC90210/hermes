from __future__ import annotations

import asyncio
import email
import logging
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import imapclient

from adapters.po_parser import parse_po
from manager.config import config
from storage.db import log_audit

logger = logging.getLogger(__name__)


def _sanitize_header(value: str) -> str:
    """Strip CR, LF, NUL to prevent MIME header injection."""
    return re.sub(r"[\r\n\x00]", "", value).strip()


_PO_SUBJECT_TOKENS: tuple[str, ...] = (
    "po",
    "purchase order",
    "order #",
    "order#",
)

_PO_FILENAME_TOKENS: tuple[str, ...] = (
    "po",
    "purchase",
    "order",
    "purch",
)

_PO_EXTENSIONS: frozenset[str] = frozenset((".pdf", ".xlsx", ".xls", ".csv"))


def _looks_like_po_subject(subject: str) -> bool:
    lower = subject.lower()
    return any(token in lower for token in _PO_SUBJECT_TOKENS)


def _looks_like_po_attachment(filename: str) -> bool:
    lower = filename.lower()
    has_ext = any(lower.endswith(ext) for ext in _PO_EXTENSIONS)
    has_token = any(token in lower for token in _PO_FILENAME_TOKENS)
    return has_ext and has_token


class EmailAgent:
    def __init__(self, cfg: Any = None) -> None:  # cfg accepted for orchestrator compat
        self._imap: imapclient.IMAPClient | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        loop = asyncio.get_running_loop()
        self._imap = await loop.run_in_executor(None, self._sync_connect)
        logger.info("IMAP connected as %s @ %s", config.email_user, config.email_host)

    def _sync_connect(self) -> imapclient.IMAPClient:
        client = imapclient.IMAPClient(
            host=config.email_host,
            port=config.email_imap_port,
            ssl=True,
            use_uid=True,
        )
        client.login(config.email_user, config.email_password)
        client.select_folder("INBOX")
        return client

    async def is_connected(self) -> bool:
        """Return True if the IMAP connection is currently active (real NOOP check)."""
        if self._imap is None:
            return False
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._imap.noop)
            return True
        except Exception:
            self._imap = None  # reset so next connect() reconnects
            return False

    async def mark_seen(self, uid: str) -> None:
        """Mark a message UID as \\Seen on the IMAP server."""
        if self._imap is None:
            return
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._imap.add_flags(uid, [b"\\Seen"]),  # type: ignore[union-attr]
        )

    # ------------------------------------------------------------------
    # Inbox polling — returns raw email dicts for the orchestrator
    # ------------------------------------------------------------------

    async def poll_inbox(self) -> list[dict[str, Any]]:
        """Poll for unseen PO emails and return them as raw dicts.

        Each dict has the shape::

            {
                "uid": str,
                "subject": str,
                "from": str,
                "body": str,
                "attachments": [(filename, content_type, bytes), ...],
            }

        Returns an empty list if the inbox is empty or the connection is not
        established (the orchestrator handles reconnection at a higher level).
        """
        if self._imap is None:
            raise RuntimeError("EmailAgent.connect() must be called before polling.")

        loop = asyncio.get_running_loop()
        raw_ids: list[int] = await loop.run_in_executor(
            None,
            lambda: self._imap.search(["UNSEEN"]),  # type: ignore[union-attr]
        )
        if not raw_ids:
            return []

        fetch_data: dict[int, dict[bytes, bytes]] = await loop.run_in_executor(
            None,
            lambda: self._imap.fetch(raw_ids, ["ENVELOPE", "BODY[]"]),  # type: ignore[union-attr]
        )

        results: list[dict[str, Any]] = []
        for uid, data in fetch_data.items():
            raw_msg = data.get(b"BODY[]", b"")
            msg = email.message_from_bytes(raw_msg)
            subject: str = msg.get("Subject", "") or ""
            sender: str = msg.get("From", "") or ""

            is_po_subject = _looks_like_po_subject(subject)
            attachments: list[tuple[str, str, bytes]] = []

            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                fname: str = part.get_filename() or ""
                content_type: str = part.get_content_type() or "application/octet-stream"
                payload = part.get_payload(decode=True)
                if fname and isinstance(payload, bytes):
                    attachments.append((fname, content_type, payload))

            has_po_attachment = any(_looks_like_po_attachment(a[0]) for a in attachments)

            if is_po_subject or has_po_attachment:
                body_parts: list[str] = []
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        raw_payload = part.get_payload(decode=True)
                        if isinstance(raw_payload, bytes):
                            body_parts.append(raw_payload.decode("utf-8", errors="replace"))
                body_text = "\n".join(body_parts)

                results.append({
                    "uid": str(uid),
                    "subject": subject,
                    "from": sender,
                    "body": body_text,
                    "attachments": attachments,
                })

        logger.info(
            "poll_inbox: %d unread, %d PO candidates", len(raw_ids), len(results)
        )
        return results

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------

    async def send_invoice(
        self,
        to: str,
        subject: str,
        body: str,
        attachment: bytes,
        filename: str,
    ) -> None:
        # Sanitize at the async boundary so callers always get clean values
        to = _sanitize_header(to)
        subject = _sanitize_header(subject)
        filename = _sanitize_header(filename).replace("/", "_").replace("\\", "_")[:200]

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._sync_send_invoice,
            to,
            subject,
            body,
            attachment,
            filename,
        )
        logger.info("Invoice sent to %s | subject=%r | attachment=%s", to, subject, filename)
        await log_audit(
            config.db_path,
            agent_name="email_agent",
            action="invoice_sent",
            details={"to": to, "subject": subject, "file": filename},
        )

    def _sync_send_invoice(
        self,
        to: str,
        subject: str,
        body: str,
        attachment: bytes,
        filename: str,
    ) -> None:
        # Inputs already sanitized by send_invoice(); kept clean here too for safety
        msg = MIMEMultipart()
        msg["From"] = config.email_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        part = MIMEApplication(attachment, Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)

        with smtplib.SMTP(config.email_smtp_host, config.email_smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.email_user, config.email_password)
            smtp.sendmail(config.email_user, to, msg.as_string())

    async def send_alert(self, to_addr: str, subject: str, body_html: str) -> None:
        """Send an HTML alert email to the given address."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._sync_send_alert,
            to_addr,
            subject,
            body_html,
        )
        logger.info("Alert sent to %s | subject=%r", to_addr, subject)

    def _sync_send_alert(self, to_addr: str, subject: str, body_html: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = config.email_user
        msg["To"] = _sanitize_header(to_addr)
        msg["Subject"] = _sanitize_header(subject)
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP(config.email_smtp_host, config.email_smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.email_user, config.email_password)
            smtp.sendmail(config.email_user, to_addr, msg.as_string())

    # ------------------------------------------------------------------
    # Standalone cycle (used when running email_agent directly)
    # ------------------------------------------------------------------

    async def run_cycle(self) -> None:
        logger.info("EmailAgent: starting cycle")
        if self._imap is None:
            await self.connect()

        try:
            emails = await self.poll_inbox()
        except Exception:
            logger.exception("poll_inbox failed")
            return

        logger.info("EmailAgent: cycle complete (%d PO candidates found)", len(emails))
