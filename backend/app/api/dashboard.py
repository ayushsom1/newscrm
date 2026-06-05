"""Dashboard KPIs + Exception queue.

The exception queue is DERIVED at query time from existing tables — no
separate persistence. That keeps the queue always in sync with reality
and avoids producer/consumer drift. Items carry `ref_url` so the FE knows
where to click through; severity maps to AUTO|APPROVE|HUMAN as in claude.md.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.advertiser import Advertiser, AdvertiserStatus, Contract, ContractStatus
from app.models.assistant import ProposedAction, ProposedActionStatus
from app.models.classified import Classified, ClassifiedStatus
from app.models.complaint import Complaint, ComplaintStatus, ComplaintTriage
from app.models.proposal import Proposal, ProposalStatus
from app.models.subscriber import Subscriber, SubscriberStatus
from app.models.tender import GovTender, TenderStatus
from app.models.user import User
from app.schemas.dashboard import ExceptionQueue, ExceptionQueueItem, KpiBlock, Kpis

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _count(db: Session, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for w in where:
        stmt = stmt.where(w)
    return int(db.scalar(stmt) or 0)


@router.get("/kpis", response_model=Kpis)
def kpis(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Kpis:
    advertisers_active = _count(
        db, Advertiser, Advertiser.status == AdvertiserStatus.ACTIVE
    )
    high_churn = _count(db, Advertiser, Advertiser.churn_band == "high")
    subs_active = _count(
        db, Subscriber, Subscriber.status == SubscriberStatus.ACTIVE
    )
    at_risk = _count(
        db,
        Subscriber,
        Subscriber.status == SubscriberStatus.ACTIVE,
        Subscriber.missed_payments >= 2,
    )
    complaints_open = _count(
        db, Complaint, Complaint.status == ComplaintStatus.OPEN
    )
    escalated_open = _count(
        db,
        Complaint,
        Complaint.status == ComplaintStatus.OPEN,
        Complaint.triage == ComplaintTriage.ESCALATED,
    )
    proposals_pending = _count(
        db, Proposal, Proposal.status == ProposalStatus.DRAFT
    )
    classifieds_active = _count(
        db,
        Classified,
        Classified.status.in_((ClassifiedStatus.QUOTED, ClassifiedStatus.PAID)),
    )

    # Lifetime revenue = sum of classifieds price_total for PAID/PUBLISHED.
    revenue_total = db.scalar(
        select(func.coalesce(func.sum(Classified.price_total), 0)).where(
            Classified.status.in_(
                (ClassifiedStatus.PAID, ClassifiedStatus.PUBLISHED)
            )
        )
    ) or Decimal("0")

    return Kpis(
        blocks=[
            KpiBlock(
                label="Active advertisers",
                value=advertisers_active,
                hint=f"{high_churn} high churn" if high_churn else None,
            ),
            KpiBlock(
                label="Active subscribers",
                value=subs_active,
                hint=f"{at_risk} at-risk" if at_risk else None,
            ),
            KpiBlock(
                label="Open complaints",
                value=complaints_open,
                hint=f"{escalated_open} escalated" if escalated_open else None,
            ),
            KpiBlock(
                label="Proposals pending approval",
                value=proposals_pending,
                hint="awaiting human review" if proposals_pending else None,
            ),
            KpiBlock(
                label="Live classifieds",
                value=classifieds_active,
                hint=None,
            ),
        ],
        revenue_running_total_inr=Decimal(revenue_total),
    )


@router.get("/exception-queue", response_model=ExceptionQueue)
def exception_queue(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ExceptionQueue:
    today = datetime.now(timezone.utc).date()
    in_30 = today + timedelta(days=30)

    items: list[ExceptionQueueItem] = []

    # 1) Contracts expiring in the next 30 days — AUTO (reminder scheduled)
    #    or APPROVE (close call worth a glance).
    expiring = db.scalars(
        select(Contract)
        .where(
            Contract.status == ContractStatus.ACTIVE,
            Contract.end_date >= today,
            Contract.end_date <= in_30,
        )
        .order_by(Contract.end_date)
        .limit(20)
    ).all()
    for c in expiring:
        days_left = (c.end_date - today).days
        adv_name = c.advertiser.name if c.advertiser else f"#{c.advertiser_id}"
        sev = "APPROVE" if days_left <= 7 else "AUTO"
        items.append(
            ExceptionQueueItem(
                type="contract_expiry",
                ref_id=c.advertiser_id,
                severity=sev,
                summary=f"{adv_name} contract expires in {days_left}d",
                detail=f"end_date={c.end_date}",
                ref_url=f"/advertisers/{c.advertiser_id}",
            )
        )

    # 2) High-churn advertisers — HUMAN.
    high_churn = db.scalars(
        select(Advertiser)
        .where(Advertiser.churn_band == "high")
        .order_by(Advertiser.churn_score.desc())
        .limit(10)
    ).all()
    for a in high_churn:
        items.append(
            ExceptionQueueItem(
                type="high_churn_advertiser",
                ref_id=a.id,
                severity="HUMAN",
                summary=f"{a.name} flagged high churn",
                detail=f"score={a.churn_score}",
                ref_url=f"/advertisers/{a.id}",
            )
        )

    # 3) Subscribers with >=2 missed payments — HUMAN.
    risky_subs = db.scalars(
        select(Subscriber)
        .where(
            Subscriber.status == SubscriberStatus.ACTIVE,
            Subscriber.missed_payments >= 2,
        )
        .order_by(Subscriber.missed_payments.desc())
        .limit(10)
    ).all()
    for s in risky_subs:
        items.append(
            ExceptionQueueItem(
                type="missed_payments",
                ref_id=s.id,
                severity="HUMAN",
                summary=f"{s.name} has {s.missed_payments} missed payments",
                detail=f"area={s.area}",
                ref_url=f"/subscribers/{s.id}",
            )
        )

    # 4) Escalated complaints awaiting human action — HUMAN.
    escalated = db.scalars(
        select(Complaint)
        .where(
            Complaint.status == ComplaintStatus.OPEN,
            Complaint.triage == ComplaintTriage.ESCALATED,
        )
        .order_by(Complaint.created_at.desc())
        .limit(10)
    ).all()
    for c in escalated:
        items.append(
            ExceptionQueueItem(
                type="escalated_complaint",
                ref_id=c.id,
                severity="HUMAN",
                summary=f"Complaint from {c.subscriber_name} escalated",
                detail=(c.text or "")[:120],
                ref_url=f"/complaints/{c.id}",
            )
        )

    # 5) Proposals waiting for approval — APPROVE.
    pending_props = db.scalars(
        select(Proposal)
        .where(Proposal.status == ProposalStatus.DRAFT)
        .order_by(Proposal.created_at.desc())
        .limit(10)
    ).all()
    for p in pending_props:
        items.append(
            ExceptionQueueItem(
                type="proposal_draft",
                ref_id=p.advertiser_id,
                severity="APPROVE",
                summary=f"Proposal awaiting approval: {p.subject[:60]}",
                detail=f"source={p.source.value}"
                + (" · needs human" if p.needs_human else ""),
                ref_url=f"/advertisers/{p.advertiser_id}",
            )
        )

    # 6) Assistant proposed actions pending review — APPROVE.
    pa_pending = db.scalars(
        select(ProposedAction)
        .where(ProposedAction.status == ProposedActionStatus.PENDING)
        .order_by(ProposedAction.created_at.desc())
        .limit(10)
    ).all()
    for pa in pa_pending:
        items.append(
            ExceptionQueueItem(
                type="proposed_action",
                ref_id=pa.id,
                severity="APPROVE",
                summary=pa.summary,
                detail=f"tool={pa.tool_name}",
                ref_url=f"/assistant",
            )
        )

    # 7) Tenders with deadlines within 14 days — APPROVE.
    tender_deadline = today + timedelta(days=14)
    upcoming_tenders = db.scalars(
        select(GovTender)
        .where(
            GovTender.status == TenderStatus.OPEN,
            GovTender.deadline >= today,
            GovTender.deadline <= tender_deadline,
        )
        .order_by(GovTender.deadline)
        .limit(10)
    ).all()
    for t in upcoming_tenders:
        days_left = (t.deadline - today).days
        items.append(
            ExceptionQueueItem(
                type="tender_deadline",
                ref_id=t.id,
                severity="APPROVE",
                summary=f"{t.title} ({t.department}) — deadline in {days_left}d",
                detail=f"est_value={t.est_value}",
                ref_url="/dashboard",
            )
        )

    counts = {"AUTO": 0, "APPROVE": 0, "HUMAN": 0}
    for it in items:
        counts[it.severity] += 1
    return ExceptionQueue(items=items, counts=counts)
