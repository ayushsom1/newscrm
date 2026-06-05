from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.advertiser import AdvertiserStatus, ContractStatus


class ContractBase(BaseModel):
    start_date: date
    end_date: date
    value: Decimal = Field(ge=0)
    slots: int = Field(ge=0, default=0)
    status: ContractStatus = ContractStatus.ACTIVE


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    value: Decimal | None = Field(default=None, ge=0)
    slots: int | None = Field(default=None, ge=0)
    status: ContractStatus | None = None


class ContractOut(ContractBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    advertiser_id: int
    created_at: datetime


class AdvertiserBase(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    annual_value: Decimal = Field(ge=0, default=Decimal("0"))
    spend_trend: Decimal = Field(default=Decimal("0"))
    proposal_open_rate: Decimal = Field(ge=0, le=100, default=Decimal("0"))
    status: AdvertiserStatus = AdvertiserStatus.ACTIVE


class AdvertiserCreate(AdvertiserBase):
    pass


class AdvertiserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    annual_value: Decimal | None = Field(default=None, ge=0)
    spend_trend: Decimal | None = None
    proposal_open_rate: Decimal | None = Field(default=None, ge=0, le=100)
    status: AdvertiserStatus | None = None


class ChurnOut(BaseModel):
    score: int | None = None
    band: str | None = None
    reasons: list[str] = []
    updated_at: datetime | None = None


class AdvertiserOut(AdvertiserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    churn: ChurnOut


class AdvertiserDetail(AdvertiserOut):
    contracts: list[ContractOut] = []
