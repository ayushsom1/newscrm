from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.subscriber import (
    Plan,
    SubscriberStatus,
    SubscriptionStatus,
)


class SubscriptionBase(BaseModel):
    plan: Plan
    start_date: date
    renew_date: date
    monthly_price: Decimal = Field(ge=0, default=Decimal("0"))
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    plan: Plan | None = None
    start_date: date | None = None
    renew_date: date | None = None
    monthly_price: Decimal | None = Field(default=None, ge=0)
    status: SubscriptionStatus | None = None


class SubscriptionOut(SubscriptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscriber_id: int
    created_at: datetime


class RenewalOut(BaseModel):
    at_risk: bool
    severity: str
    reasons: list[str] = []
    days_to_renew: int | None = None


class SubscriberBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=4, max_length=40)
    area: str = Field(min_length=1, max_length=80)
    address: str | None = None
    plan: Plan = Plan.DAILY
    status: SubscriberStatus = SubscriberStatus.ACTIVE
    missed_payments: int = Field(ge=0, default=0)


class SubscriberCreate(SubscriberBase):
    pass


class SubscriberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=4, max_length=40)
    area: str | None = Field(default=None, min_length=1, max_length=80)
    address: str | None = None
    plan: Plan | None = None
    status: SubscriberStatus | None = None
    missed_payments: int | None = Field(default=None, ge=0)


class SubscriberOut(SubscriberBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    renewal: RenewalOut


class SubscriberDetail(SubscriberOut):
    subscriptions: list[SubscriptionOut] = []


class AreaForecast(BaseModel):
    area: str
    active_subs: int
    newsstand_buffer: int = 0
    returns_pct: float
    target: int


class ForecastSummary(BaseModel):
    total_target: int
    total_active: int
    areas: list[AreaForecast]
