"""APScheduler integration. Started in the FastAPI lifespan.

Defaults are conservative:
  * Nightly churn recompute at 02:30 server time.
  * Daily expire-contracts at 02:45.
  * Daily renewal reminders at 09:00 (so reminders go out at a sane hour).

The runner is fully idempotent per (job_name, window_date) so duplicate
fires (e.g. process restart) are safe.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.runner import run_job

log = logging.getLogger(__name__)


def _safe_run(job_name: str) -> None:
    try:
        run_job(job_name, triggered_by="SCHEDULER")
    except Exception:
        log.exception("scheduled run of %s failed", job_name)


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _safe_run,
        CronTrigger(hour=2, minute=30),
        args=["nightly_churn_recompute"],
        id="nightly_churn_recompute",
        replace_existing=True,
    )
    scheduler.add_job(
        _safe_run,
        CronTrigger(hour=2, minute=45),
        args=["daily_expire_contracts"],
        id="daily_expire_contracts",
        replace_existing=True,
    )
    scheduler.add_job(
        _safe_run,
        CronTrigger(hour=9, minute=0),
        args=["daily_renewal_reminders"],
        id="daily_renewal_reminders",
        replace_existing=True,
    )
    return scheduler
