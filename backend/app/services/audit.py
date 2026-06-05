"""Audit log helper. Caller commits."""
from typing import Any

from sqlalchemy.orm import Session

from app.models.complaint import AuditLog
from app.models.user import User


def write_audit(
    db: Session,
    *,
    actor: User | None,
    is_ai: bool = False,
    action: str,
    entity: str,
    entity_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    if is_ai:
        actor_str = "AI"
    elif actor is not None:
        actor_str = f"USER:{actor.id}"
    else:
        actor_str = "SYSTEM"
    row = AuditLog(
        actor=actor_str,
        action=action,
        entity=entity,
        entity_id=entity_id,
        payload=payload,
    )
    db.add(row)
    return row
