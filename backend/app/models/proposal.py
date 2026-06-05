import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ProposalSource(str, enum.Enum):
    AI_DRAFT = "AI_DRAFT"
    HUMAN = "HUMAN"


class ProposalStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SENT = "SENT"
    REJECTED = "REJECTED"


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    advertiser_id: Mapped[int] = mapped_column(
        ForeignKey("advertisers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[ProposalSource] = mapped_column(
        Enum(ProposalSource, name="proposal_source"), nullable=False
    )
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="proposal_status"),
        nullable=False,
        default=ProposalStatus.DRAFT,
    )
    # When true, this proposal cannot be auto-sent or one-click-approved by
    # non-ADMIN; a human needs to review it. Set automatically for high-churn
    # accounts.
    needs_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_human_reason: Mapped[str | None] = mapped_column(String(200))

    model_used: Mapped[str | None] = mapped_column(String(80))

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
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
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    advertiser = relationship("Advertiser")
