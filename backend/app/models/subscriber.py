import enum
from datetime import date, datetime

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


class SubscriberStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Plan(str, enum.Enum):
    DAILY = "DAILY"
    WEEKEND = "WEEKEND"
    SUNDAY_ONLY = "SUNDAY_ONLY"


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    area: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[Plan] = mapped_column(
        Enum(Plan, name="subscriber_plan"), nullable=False, default=Plan.DAILY
    )
    status: Mapped[SubscriberStatus] = mapped_column(
        Enum(SubscriberStatus, name="subscriber_status"),
        nullable=False,
        default=SubscriberStatus.ACTIVE,
    )
    missed_payments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="subscriber",
        cascade="all, delete-orphan",
        order_by="Subscription.start_date.desc()",
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(
        ForeignKey("subscribers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan: Mapped[Plan] = mapped_column(Enum(Plan, name="subscriber_plan"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    renew_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    monthly_price: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscriber: Mapped[Subscriber] = relationship(back_populates="subscriptions")


class AreaReturns(Base):
    """Per-area returns ratio hint for the print-run forecast.

    A value of 0.05 means historically 5% of copies are unsold in this area.
    """

    __tablename__ = "area_returns"

    area: Mapped[str] = mapped_column(String(80), primary_key=True)
    returns_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
