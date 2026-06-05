from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.complaint import (
    ComplaintChannel,
    ComplaintStatus,
    ComplaintTriage,
)


class ComplaintBase(BaseModel):
    subscriber_name: str = Field(min_length=1, max_length=160)
    subscriber_phone: str | None = Field(default=None, max_length=40)
    area: str | None = Field(default=None, max_length=80)
    text: str = Field(min_length=1)
    channel: ComplaintChannel = ComplaintChannel.PHONE


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintUpdate(BaseModel):
    resolution: str | None = None
    status: ComplaintStatus | None = None
    assigned_to_id: int | None = None


class ComplaintOut(ComplaintBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    triage: ComplaintTriage
    triage_reason: str | None
    triage_source: str | None
    resolution: str | None
    status: ComplaintStatus
    assigned_to_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class TriageResponse(BaseModel):
    auto: bool
    resolution: str
    source: str  # "AI" | "ENGINE"
    reason: str


class AssignBody(BaseModel):
    user_id: int


class ResolveBody(BaseModel):
    resolution: str = Field(min_length=1)
