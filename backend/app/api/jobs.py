from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.jobs.runner import JOBS, run_job
from app.models.job import JobRun
from app.models.user import User, UserRole
from app.schemas.job import JobInfo, JobList, JobRunOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobList)
def list_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> JobList:
    out: list[JobInfo] = []
    for name in JOBS.keys():
        last = db.scalar(
            select(JobRun)
            .where(JobRun.job_name == name)
            .order_by(JobRun.started_at.desc())
            .limit(1)
        )
        out.append(
            JobInfo(
                name=name,
                last_run=JobRunOut.model_validate(last) if last else None,
            )
        )
    return JobList(jobs=out)


@router.get("/runs", response_model=list[JobRunOut])
def list_runs(
    job: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[JobRun]:
    stmt = select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)
    if job:
        stmt = stmt.where(JobRun.job_name == job)
    return list(db.scalars(stmt).all())


@router.post("/{name}/run", response_model=JobRunOut)
def trigger_job(
    name: str,
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> JobRun:
    if name not in JOBS:
        raise HTTPException(status_code=404, detail="unknown job")
    return run_job(name, triggered_by=f"USER:{actor.id}")
