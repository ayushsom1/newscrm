"""Autonomy thresholds — the AI "dial".

Stored as a singleton row (id=1). All boolean fields default to "safe":
AI is allowed to act on the routine cases, never on sensitive ones, and
high-churn always escalates regardless of any other setting.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


SINGLETON_ID = 1


class AutonomyConfig(Base):
    __tablename__ = "autonomy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=SINGLETON_ID)

    # Complaint triage
    triage_ai_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    triage_auto_resolve_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Proposal drafting
    ai_draft_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    high_churn_always_needs_human: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Assistant
    assistant_actions_require_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Locale & commercial config (per claude.md §13)
    locale: Mapped[str] = mapped_column(
        String(4), nullable=False, default="IN"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by_id: Mapped[int | None] = mapped_column(Integer)
