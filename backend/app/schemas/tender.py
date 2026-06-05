from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.tender import TenderStatus


class TenderBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=120)
    deadline: date
    est_value: Decimal = Field(ge=0, default=Decimal("0"))
    status: TenderStatus = TenderStatus.OPEN
    notes: str | None = None


class TenderCreate(TenderBase):
    pass


class TenderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    department: str | None = Field(default=None, min_length=1, max_length=120)
    deadline: date | None = None
    est_value: Decimal | None = Field(default=None, ge=0)
    status: TenderStatus | None = None
    notes: str | None = None


class TenderOut(TenderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
