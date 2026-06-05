"""Job runner: registry + transactional execution + idempotency."""
from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.jobs.tasks import (
    JobReport,
    daily_expire_contracts,
    daily_renewal_reminders,
    nightly_churn_recompute,
)
from app.models.job import JobRun, JobStatus

log = logging.getLogger(__name__)

JobFn = Callable[[Session, date], JobReport]

JOBS: dict[str, JobFn] = {
    "nightly_churn_recompute": nightly_churn_recompute,
    "daily_expire_contracts": daily_expire_contracts,
    "daily_renewal_reminders": daily_renewal_reminders,
}


def _today() -> date:
    return datetime.now(timezone.utc).date()


def run_job(
    name: str,
    *,
    triggered_by: str = "SCHEDULER",
    window_date: date | None = None,
) -> JobRun:
    """Execute a registered job. Idempotent for (name, window_date).

    Returns the JobRun row (committed). If the job has already run for the
    window, returns the existing row with status SKIPPED ignored.
    """
    if name not in JOBS:
        raise KeyError(f"unknown job: {name}")

    fn = JOBS[name]
    window = window_date or _today()

    db = SessionLocal()
    try:
        # Insert the JobRun row first so a uniqueness clash short-circuits
        # any work — we never re-run a window. SUCCESS row goes in after work
        # completes; we update the same row.
        run = JobRun(
            job_name=name,
            window_date=window,
            status=JobStatus.SUCCESS,  # provisional; overwritten on error
            triggered_by=triggered_by,
        )
        db.add(run)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = db.query(JobRun).filter_by(
                job_name=name, window_date=window
            ).one()
            return existing

        try:
            report: JobReport = fn(db, window)
            run.items_processed = report.items_processed
            run.notifications_sent = report.notifications_sent
            run.report = asdict(report)["details"]
            run.status = JobStatus.SUCCESS
        except Exception as e:  # noqa: BLE001 — we want the trace
            log.exception("job %s failed", name)
            db.rollback()
            # Re-fetch / re-insert the row with FAILED status. We've rolled
            # back the work; the JobRun row must still be recorded so the
            # scheduler can see it ran.
            run = JobRun(
                job_name=name,
                window_date=window,
                status=JobStatus.FAILED,
                triggered_by=triggered_by,
                error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[:1500]}",
            )
            db.add(run)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                # Another concurrent run beat us — return whichever exists.
                return db.query(JobRun).filter_by(
                    job_name=name, window_date=window
                ).one()

        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()
