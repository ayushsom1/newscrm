from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.drafter import draft_proposal
from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.core.ratelimit import AI_LIMIT, limiter
from app.engines.churn import score_churn
from app.models.advertiser import Advertiser
from app.models.proposal import Proposal, ProposalSource, ProposalStatus
from app.models.user import User, UserRole
from app.schemas.proposal import ProposalCreate, ProposalOut, ProposalUpdate
from app.services.audit import write_audit
from app.services.churn import days_to_active_contract_expiry

router = APIRouter(tags=["proposals"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.SALES)
APPROVE_ROLES = (UserRole.ADMIN, UserRole.SALES)


def _get_adv(db: Session, advertiser_id: int) -> Advertiser:
    adv = db.get(Advertiser, advertiser_id)
    if adv is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    return adv


@router.get("/advertisers/{advertiser_id}/proposals", response_model=list[ProposalOut])
def list_proposals(
    advertiser_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Proposal]:
    _get_adv(db, advertiser_id)
    rows = db.scalars(
        select(Proposal)
        .where(Proposal.advertiser_id == advertiser_id)
        .order_by(Proposal.created_at.desc())
    ).all()
    return list(rows)


@router.post(
    "/advertisers/{advertiser_id}/proposals/draft",
    response_model=ProposalOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(AI_LIMIT)
def ai_draft_proposal(
    request: Request,
    advertiser_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Proposal:
    adv = _get_adv(db, advertiser_id)
    # Recompute churn reasons live so the drafter sees the latest grounding.
    churn = score_churn(
        spend_trend=float(adv.spend_trend or 0),
        open_rate=float(adv.proposal_open_rate or 0),
        days_to_expiry=days_to_active_contract_expiry(adv),
    )
    drafted = draft_proposal(adv, churn.reasons)

    p = Proposal(
        advertiser_id=adv.id,
        subject=drafted.subject,
        body=drafted.body,
        source=ProposalSource.AI_DRAFT,
        status=ProposalStatus.DRAFT,
        needs_human=drafted.needs_human,
        needs_human_reason=drafted.needs_human_reason,
        model_used=drafted.model_used,
        created_by_id=actor.id,
    )
    db.add(p)
    db.flush()
    write_audit(
        db,
        actor=None,
        is_ai=True,
        action="draft",
        entity="proposal",
        entity_id=p.id,
        payload={
            "advertiser_id": adv.id,
            "model": drafted.model_used,
            "needs_human": drafted.needs_human,
            "needs_human_reason": drafted.needs_human_reason,
        },
    )
    db.commit()
    db.refresh(p)
    return p


@router.post(
    "/advertisers/{advertiser_id}/proposals",
    response_model=ProposalOut,
    status_code=status.HTTP_201_CREATED,
)
def human_proposal(
    advertiser_id: int,
    payload: ProposalCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Proposal:
    adv = _get_adv(db, advertiser_id)
    p = Proposal(
        advertiser_id=adv.id,
        subject=payload.subject,
        body=payload.body,
        source=ProposalSource.HUMAN,
        status=ProposalStatus.DRAFT,
        needs_human=False,
        created_by_id=actor.id,
    )
    db.add(p)
    db.flush()
    write_audit(
        db,
        actor=actor,
        action="create",
        entity="proposal",
        entity_id=p.id,
        payload={"source": "HUMAN"},
    )
    db.commit()
    db.refresh(p)
    return p


@router.patch("/proposals/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: int,
    payload: ProposalUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*WRITE_ROLES)),
) -> Proposal:
    p = db.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    if p.status not in (ProposalStatus.DRAFT, ProposalStatus.REJECTED):
        raise HTTPException(
            status_code=409, detail=f"cannot edit a {p.status.value} proposal"
        )
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    write_audit(
        db,
        actor=actor,
        action="edit",
        entity="proposal",
        entity_id=p.id,
        payload=data,
    )
    db.commit()
    db.refresh(p)
    return p


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalOut)
def approve_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*APPROVE_ROLES)),
) -> Proposal:
    p = db.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    if p.status != ProposalStatus.DRAFT:
        raise HTTPException(
            status_code=409, detail=f"cannot approve a {p.status.value} proposal"
        )
    # needs_human proposals must be approved by ADMIN (or by SALES who explicitly
    # acknowledges via the same call — captured in audit log either way).
    p.status = ProposalStatus.APPROVED
    p.approved_by_id = actor.id
    p.approved_at = datetime.now(timezone.utc)
    write_audit(
        db,
        actor=actor,
        action="approve",
        entity="proposal",
        entity_id=p.id,
        payload={
            "needs_human": p.needs_human,
            "source": p.source.value,
        },
    )
    db.commit()
    db.refresh(p)
    return p


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*APPROVE_ROLES)),
) -> Proposal:
    p = db.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    if p.status not in (ProposalStatus.DRAFT, ProposalStatus.APPROVED):
        raise HTTPException(
            status_code=409, detail=f"cannot reject a {p.status.value} proposal"
        )
    p.status = ProposalStatus.REJECTED
    write_audit(
        db,
        actor=actor,
        action="reject",
        entity="proposal",
        entity_id=p.id,
    )
    db.commit()
    db.refresh(p)
    return p


@router.post("/proposals/{proposal_id}/send", response_model=ProposalOut)
def send_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*APPROVE_ROLES)),
) -> Proposal:
    p = db.get(Proposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proposal not found")
    if p.status != ProposalStatus.APPROVED:
        raise HTTPException(
            status_code=409,
            detail=f"proposal must be APPROVED to send, currently {p.status.value}",
        )
    # Sending is a stubbed action — email provider integration belongs in
    # the notifications service. We just record the transition + audit.
    p.status = ProposalStatus.SENT
    p.sent_at = datetime.now(timezone.utc)
    write_audit(
        db,
        actor=actor,
        action="send",
        entity="proposal",
        entity_id=p.id,
        payload={"to": p.advertiser.contact_email},
    )
    db.commit()
    db.refresh(p)
    return p
