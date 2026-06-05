import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ClassifiedStatus(str, enum.Enum):
    QUOTED = "QUOTED"
    PAID = "PAID"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class Classified(Base):
    __tablename__ = "classifieds"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    locale: Mapped[str] = mapped_column(String(4), nullable=False, default="IN")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")

    price_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[ClassifiedStatus] = mapped_column(
        Enum(ClassifiedStatus, name="classified_status"),
        nullable=False,
        default=ClassifiedStatus.QUOTED,
    )
    publish_date: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
