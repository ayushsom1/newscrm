import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class JobStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class JobRun(Base):
    """One row per (job_name, window_date) — unique so jobs are idempotent
    within a day. Holds counts and an arbitrary report JSON."""

    __tablename__ = "job_runs"
    __table_args__ = (
        UniqueConstraint("job_name", "window_date", name="uq_job_runs_job_window"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    window_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False
    )
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notifications_sent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    report: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    triggered_by: Mapped[str] = mapped_column(
        String(40), nullable=False, default="SCHEDULER"
    )  # "SCHEDULER" or "USER:<id>"
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
