from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.proposal import ProposalSource, ProposalStatus


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    advertiser_id: int
    subject: str
    body: str
    source: ProposalSource
    status: ProposalStatus
    needs_human: bool
    needs_human_reason: str | None
    model_used: str | None
    created_by_id: int | None
    approved_by_id: int | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    sent_at: datetime | None


class ProposalCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


class ProposalUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
