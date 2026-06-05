import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AdvertiserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PROSPECT = "PROSPECT"


class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Advertiser(Base):
    __tablename__ = "advertisers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(80))
    contact_name: Mapped[str | None] = mapped_column(String(120))
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    contact_email: Mapped[str | None] = mapped_column(String(255))

    annual_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    spend_trend: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )  # YoY pct, e.g. -15.50 means -15.5%
    proposal_open_rate: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0
    )  # 0..100

    status: Mapped[AdvertiserStatus] = mapped_column(
        Enum(AdvertiserStatus, name="advertiser_status"),
        nullable=False,
        default=AdvertiserStatus.ACTIVE,
    )

    churn_score: Mapped[int | None] = mapped_column(Integer)  # cached snapshot
    churn_band: Mapped[str | None] = mapped_column(String(8))  # low|med|high
    churn_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="advertiser",
        cascade="all, delete-orphan",
        order_by="Contract.start_date.desc()",
    )


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    advertiser_id: Mapped[int] = mapped_column(
        ForeignKey("advertisers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    slots: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status"),
        nullable=False,
        default=ContractStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    advertiser: Mapped[Advertiser] = relationship(back_populates="contracts")
