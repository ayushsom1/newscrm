import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ComplaintTriage(str, enum.Enum):
    PENDING = "PENDING"
    AUTO = "AUTO"
    ESCALATED = "ESCALATED"


class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ComplaintChannel(str, enum.Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    WALK_IN = "WALK_IN"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_name: Mapped[str] = mapped_column(String(160), nullable=False)
    subscriber_phone: Mapped[str | None] = mapped_column(String(40), index=True)
    area: Mapped[str | None] = mapped_column(String(80))

    text: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[ComplaintChannel] = mapped_column(
        Enum(ComplaintChannel, name="complaint_channel"),
        nullable=False,
        default=ComplaintChannel.PHONE,
    )

    triage: Mapped[ComplaintTriage] = mapped_column(
        Enum(ComplaintTriage, name="complaint_triage"),
        nullable=False,
        default=ComplaintTriage.PENDING,
    )
    triage_reason: Mapped[str | None] = mapped_column(Text)
    triage_source: Mapped[str | None] = mapped_column(String(20))  # "AI" | "ENGINE"
    resolution: Mapped[str | None] = mapped_column(Text)

    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status"),
        nullable=False,
        default=ComplaintStatus.OPEN,
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(40), nullable=False)  # "AI" or "USER:<id>"
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
