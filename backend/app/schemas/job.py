from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.job import JobStatus


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_name: str
    window_date: date
    status: JobStatus
    items_processed: int
    notifications_sent: int
    report: dict[str, Any] | None
    error: str | None
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None


class JobInfo(BaseModel):
    name: str
    last_run: JobRunOut | None


class JobList(BaseModel):
    jobs: list[JobInfo]
