from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.classified import ClassifiedStatus

Locale = Literal["IN", "NP"]


class QuoteIn(BaseModel):
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    duration_days: int = Field(ge=1, le=365)
    locale: Locale = "IN"


class QuoteOut(BaseModel):
    currency: str
    tax_label: str
    word_count: int
    net: Decimal
    tax: Decimal
    total: Decimal
    breakdown: dict[str, str]


class ClassifiedCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str = Field(min_length=4, max_length=40)
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    duration_days: int = Field(ge=1, le=365)
    locale: Locale = "IN"
    publish_date: date | None = None


class ClassifiedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_name: str
    customer_phone: str
    text: str
    word_count: int
    category: str
    duration_days: int
    locale: str
    currency: str
    price_net: Decimal
    price_tax: Decimal
    price_total: Decimal
    status: ClassifiedStatus
    publish_date: date | None
    created_at: datetime
    paid_at: datetime | None
    published_at: datetime | None
