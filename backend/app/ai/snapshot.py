"""Read-only CRM snapshot for grounding the assistant.

Design constraints:
  * Aggregates and counts, not customer PII.
  * No payment data, no full subscriber lists, no AuditLog entries.
  * Small JSON — model context, not a data dump.
  * Always cap arrays.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.advertiser import Advertiser, AdvertiserStatus, Contract, ContractStatus
from app.models.classified import Classified, ClassifiedStatus
from app.models.complaint import Complaint, ComplaintStatus, ComplaintTriage
from app.models.proposal import Proposal, ProposalStatus
from app.models.subscriber import Subscriber, SubscriberStatus

CAP = 5  # max items per list


def _count(db: Session, model, *where) -> int:
    stmt = select(func.count()).select_from(model)
    for w in where:
        stmt = stmt.where(w)
    return int(db.scalar(stmt) or 0)


def build_crm_snapshot(db: Session) -> dict:
    today = datetime.now(timezone.utc).date()
    in_30 = today + timedelta(days=30)

    # Counts
    advertisers_active = _count(db, Advertiser, Advertiser.status == AdvertiserStatus.ACTIVE)
    advertisers_high_churn = _count(db, Advertiser, Advertiser.churn_band == "high")
    subs_active = _count(db, Subscriber, Subscriber.status == SubscriberStatus.ACTIVE)
    classifieds_quoted = _count(db, Classified, Classified.status == ClassifiedStatus.QUOTED)
    classifieds_paid = _count(db, Classified, Classified.status == ClassifiedStatus.PAID)
    complaints_open = _count(db, Complaint, Complaint.status == ComplaintStatus.OPEN)
    complaints_escalated = _count(
        db, Complaint,
        Complaint.status == ComplaintStatus.OPEN,
        Complaint.triage == ComplaintTriage.ESCALATED,
    )
    proposals_pending = _count(db, Proposal, Proposal.status == ProposalStatus.DRAFT)

    # Expiring contracts in next 30d
    expiring_rows = db.scalars(
        select(Contract)
        .where(
            Contract.status == ContractStatus.ACTIVE,
            Contract.end_date <= in_30,
            Contract.end_date >= today,
        )
        .order_by(Contract.end_date)
        .limit(CAP)
    ).all()
    expiring = [
        {
            "advertiser_id": c.advertiser_id,
            "advertiser_name": c.advertiser.name if c.advertiser else None,
            "end_date": str(c.end_date),
            "days_left": (c.end_date - today).days,
        }
        for c in expiring_rows
    ]

    # At-risk subscriptions (renew within 14d OR >=2 missed payments)
    at_risk_rows = db.scalars(
        select(Subscriber)
        .where(
            Subscriber.status == SubscriberStatus.ACTIVE,
            (Subscriber.missed_payments >= 2),
        )
        .order_by(Subscriber.missed_payments.desc())
        .limit(CAP)
    ).all()
    at_risk = [
        {
            "subscriber_id": s.id,
            "name": s.name,
            "area": s.area,
            "missed_payments": s.missed_payments,
        }
        for s in at_risk_rows
    ]

    # Recent escalated complaints awaiting human action
    escalated_rows = db.scalars(
        select(Complaint)
        .where(
            Complaint.status == ComplaintStatus.OPEN,
            Complaint.triage == ComplaintTriage.ESCALATED,
        )
        .order_by(Complaint.created_at.desc())
        .limit(CAP)
    ).all()
    escalated = [
        {
            "complaint_id": c.id,
            "subscriber_name": c.subscriber_name,
            "area": c.area,
            "channel": c.channel.value,
            "snippet": (c.text or "")[:120],
        }
        for c in escalated_rows
    ]

    return {
        "today": str(today),
        "counts": {
            "advertisers_active": advertisers_active,
            "advertisers_high_churn": advertisers_high_churn,
            "subscribers_active": subs_active,
            "classifieds_quoted": classifieds_quoted,
            "classifieds_paid": classifieds_paid,
            "complaints_open": complaints_open,
            "complaints_escalated_open": complaints_escalated,
            "proposals_pending_approval": proposals_pending,
        },
        "expiring_contracts_30d": expiring,
        "at_risk_subscribers": at_risk,
        "escalated_complaints": escalated,
    }
