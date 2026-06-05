import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TenderStatus(str, enum.Enum):
    OPEN = "OPEN"
    SUBMITTED = "SUBMITTED"
    WON = "WON"
    LOST = "LOST"
    CLOSED = "CLOSED"


class GovTender(Base):
    __tablename__ = "gov_tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    est_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[TenderStatus] = mapped_column(
        Enum(TenderStatus, name="tender_status"),
        nullable=False,
        default=TenderStatus.OPEN,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
