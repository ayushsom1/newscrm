from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AutonomyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    triage_ai_enabled: bool
    triage_auto_resolve_enabled: bool
    ai_draft_enabled: bool
    high_churn_always_needs_human: bool
    assistant_actions_require_admin: bool
    locale: str
    updated_at: datetime
    updated_by_id: int | None


class AutonomyUpdate(BaseModel):
    triage_ai_enabled: bool | None = None
    triage_auto_resolve_enabled: bool | None = None
    ai_draft_enabled: bool | None = None
    high_churn_always_needs_human: bool | None = None
    assistant_actions_require_admin: bool | None = None
    locale: str | None = Field(default=None, pattern="^(IN|NP)$")
