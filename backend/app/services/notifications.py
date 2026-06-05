"""Notification provider interface.

Email by default; SMS/WhatsApp can plug in later by adding another Notifier
implementation. The notifier writes an AuditLog row for every send so we
always have a record, even when the actual transport is stubbed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.audit import write_audit

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str
    entity: str | None = None
    entity_id: int | None = None


class Notifier(Protocol):
    name: str

    def send_email(self, db: Session, msg: EmailMessage) -> bool: ...


class ConsoleNotifier:
    """Logs the email to stdout. Default in dev; safe in tests."""

    name = "console"

    def send_email(self, db: Session, msg: EmailMessage) -> bool:
        log.info(
            "[email/console] to=%s subject=%r body=%r",
            msg.to, msg.subject, msg.body[:200],
        )
        write_audit(
            db,
            actor=None,
            action="notify_email",
            entity=msg.entity or "notification",
            entity_id=msg.entity_id,
            payload={
                "provider": "console",
                "to": msg.to,
                "subject": msg.subject,
            },
        )
        return True


class ResendNotifier:
    """Stub: would call Resend's HTTP API. Not enabled unless RESEND_API_KEY
    is set; falls back to console otherwise."""

    name = "resend"

    def send_email(self, db: Session, msg: EmailMessage) -> bool:
        # Intentionally not implementing the HTTP call here — pluggable hook
        # for production. We still record the intent.
        log.info("[email/resend-stub] to=%s subject=%r", msg.to, msg.subject)
        write_audit(
            db,
            actor=None,
            action="notify_email",
            entity=msg.entity or "notification",
            entity_id=msg.entity_id,
            payload={
                "provider": "resend",
                "to": msg.to,
                "subject": msg.subject,
                "stubbed": True,
            },
        )
        return True


def get_notifier() -> Notifier:
    if settings.RESEND_API_KEY:
        return ResendNotifier()
    return ConsoleNotifier()
