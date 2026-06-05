from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.triage import triage_complaint
from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.core.ratelimit import AI_LIMIT, limiter
from app.models.complaint import (
    Complaint,
    ComplaintStatus,
    ComplaintTriage,
)
from app.models.user import User, UserRole
from app.schemas.complaint import (
    AssignBody,
    ComplaintCreate,
    ComplaintOut,
    ComplaintUpdate,
    ResolveBody,
    TriageResponse,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/complaints", tags=["complaints"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CIRCULATION, UserRole.SALES)


@router.get("", response_model=list[ComplaintOut])
def list_complaints(
    q: str | None = Query(default=None),
    triage_filter: ComplaintTriage | None = Query(default=None, alias="triage"),
    status_filter: ComplaintStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Complaint]:
    stmt = select(Complaint)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Complaint.subscriber_name.ilike(like),
                Complaint.subscriber_phone.ilike(like),
                Complaint.text.ilike(like),
            )
        )
    if triage_filter:
        stmt = stmt.where(Complaint.triage == triage_filter)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    stmt = stmt.order_by(Complaint.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    return c


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Complaint:
    c = Complaint(**payload.model_dump())
    db.add(c)
    db.flush()
    write_audit(
        db,
        actor=actor,
        action="create",
        entity="complaint",
        entity_id=c.id,
        payload={"channel": c.channel.value},
    )
    db.commit()
    db.refresh(c)
    return c


@router.post("/{complaint_id}/triage", response_model=TriageResponse)
@limiter.limit(AI_LIMIT)
def run_triage(
    request: Request,
    complaint_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> TriageResponse:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    if c.status != ComplaintStatus.OPEN:
        raise HTTPException(
            status_code=409, detail=f"cannot triage a {c.status.value} complaint"
        )

    result = triage_complaint(c.text)

    c.triage = ComplaintTriage.AUTO if result.auto else ComplaintTriage.ESCALATED
    c.triage_source = result.source
    c.triage_reason = result.reason
    if result.auto:
        c.resolution = result.resolution
        c.status = ComplaintStatus.RESOLVED
        c.resolved_at = datetime.now(timezone.utc)
    else:
        # ESCALATED: do NOT auto-resolve; a human takes it from here.
        c.resolution = None

    write_audit(
        db,
        actor=actor if result.source == "ENGINE" else None,
        is_ai=result.source == "AI",
        action="triage",
        entity="complaint",
        entity_id=c.id,
        payload={
            "auto": result.auto,
            "source": result.source,
            "reason": result.reason,
            "resolution": result.resolution,
        },
    )
    db.commit()
    db.refresh(c)
    return TriageResponse(
        auto=result.auto,
        resolution=result.resolution,
        source=result.source,
        reason=result.reason,
    )


@router.post("/{complaint_id}/assign", response_model=ComplaintOut)
def assign_complaint(
    complaint_id: int,
    body: AssignBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    assignee = db.get(User, body.user_id)
    if assignee is None:
        raise HTTPException(status_code=400, detail="user not found")
    c.assigned_to_id = assignee.id
    write_audit(
        db,
        actor=actor,
        action="assign",
        entity="complaint",
        entity_id=c.id,
        payload={"assigned_to_id": assignee.id},
    )
    db.commit()
    db.refresh(c)
    return c


@router.post("/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    complaint_id: int,
    body: ResolveBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    if c.status == ComplaintStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="already resolved")
    c.resolution = body.resolution.strip()
    c.status = ComplaintStatus.RESOLVED
    c.resolved_at = datetime.now(timezone.utc)
    write_audit(
        db,
        actor=actor,
        action="resolve",
        entity="complaint",
        entity_id=c.id,
        payload={"resolution": c.resolution},
    )
    db.commit()
    db.refresh(c)
    return c


@router.patch("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Complaint:
    c = db.get(Complaint, complaint_id)
    if c is None:
        raise HTTPException(status_code=404, detail="complaint not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    write_audit(
        db,
        actor=actor,
        action="update",
        entity="complaint",
        entity_id=c.id,
        payload=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(c)
    return c
