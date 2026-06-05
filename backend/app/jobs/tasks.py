"""Job tasks — each is a pure function `(db, today) -> JobReport`.

No commits inside the tasks; the runner manages the transaction and writes
the JobRun row. Idempotency lives at the runner layer (unique constraint
on job_name + window_date).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.advertiser import Advertiser, Contract, ContractStatus
from app.models.subscriber import Subscriber, SubscriberStatus, Subscription, SubscriptionStatus
from app.services.churn import recompute_churn
from app.services.notifications import EmailMessage, get_notifier


@dataclass
class JobReport:
    items_processed: int = 0
    notifications_sent: int = 0
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# nightly_churn_recompute
# ---------------------------------------------------------------------------
def nightly_churn_recompute(db: Session, today: date) -> JobReport:
    """Re-score churn for every active advertiser and cache the snapshot."""
    rows = db.scalars(
        select(Advertiser).options(selectinload(Advertiser.contracts))
    ).all()
    bands: dict[str, int] = {"low": 0, "med": 0, "high": 0}
    for adv in rows:
        recompute_churn(adv)
        if adv.churn_band in bands:
            bands[adv.churn_band] += 1
    return JobReport(
        items_processed=len(rows),
        notifications_sent=0,
        details={"bands": bands},
    )


# ---------------------------------------------------------------------------
# daily_expire_contracts
# ---------------------------------------------------------------------------
def daily_expire_contracts(db: Session, today: date) -> JobReport:
    """Mark active contracts whose end_date has passed as EXPIRED.

    Keeps churn snapshots accurate the next time advertisers are touched.
    """
    rows = db.scalars(
        select(Contract).where(
            Contract.status == ContractStatus.ACTIVE,
            Contract.end_date < today,
        )
    ).all()
    for c in rows:
        c.status = ContractStatus.EXPIRED
    return JobReport(
        items_processed=len(rows),
        notifications_sent=0,
        details={"contract_ids": [c.id for c in rows]},
    )


# ---------------------------------------------------------------------------
# daily_renewal_reminders
# ---------------------------------------------------------------------------
REMINDER_WINDOWS_DAYS = (14, 7, 3, 1)


def daily_renewal_reminders(db: Session, today: date) -> JobReport:
    """Email reminders to advertisers (contract expiring) and subscribers
    (subscription renewing) on specific day-out windows.

    A reminder is sent once per (advertiser, end_date, window) — derived
    purely from the difference between today and the end/renew date, so the
    job is idempotent without a separate sent_reminders table for the dev
    cut. The window list keeps the volume bounded.
    """
    notifier = get_notifier()
    sent = 0
    advertiser_hits: list[dict] = []
    subscriber_hits: list[dict] = []

    # Advertisers — expiring contracts
    contracts = db.scalars(
        select(Contract)
        .options(selectinload(Contract.advertiser))
        .where(Contract.status == ContractStatus.ACTIVE)
    ).all()
    for c in contracts:
        days_left = (c.end_date - today).days
        if days_left not in REMINDER_WINDOWS_DAYS:
            continue
        adv = c.advertiser
        if adv is None or not adv.contact_email:
            continue
        msg = EmailMessage(
            to=adv.contact_email,
            subject=f"Renewal reminder — your contract ends in {days_left} day(s)",
            body=(
                f"Hi {adv.contact_name or adv.name},\n\n"
                f"This is a friendly reminder that your contract is set to "
                f"end on {c.end_date}. Our team would love to discuss a "
                "renewal whenever it suits you.\n\n"
                "— the News CRM team"
            ),
            entity="advertiser",
            entity_id=adv.id,
        )
        if notifier.send_email(db, msg):
            sent += 1
            advertiser_hits.append(
                {"advertiser_id": adv.id, "days_left": days_left}
            )

    # Subscribers — renewing subscriptions
    subs = db.scalars(
        select(Subscription)
        .options(selectinload(Subscription.subscriber))
        .where(Subscription.status == SubscriptionStatus.ACTIVE)
    ).all()
    for s in subs:
        days_left = (s.renew_date - today).days
        if days_left not in REMINDER_WINDOWS_DAYS:
            continue
        sub = s.subscriber
        if sub is None or sub.status != SubscriberStatus.ACTIVE:
            continue
        # We don't have email on subscribers; for now, send to a synthesised
        # local address so the audit row records the intent. Real SMS plug
        # would replace this.
        to = f"sub-{sub.id}@subscriber.local"
        msg = EmailMessage(
            to=to,
            subject=f"Your subscription renews in {days_left} day(s)",
            body=(
                f"Hi {sub.name},\n\n"
                "A quick note that your subscription is up for renewal on "
                f"{s.renew_date}. If you'd like to make any changes, just "
                "reply to this message.\n\n"
                "— Circulation team"
            ),
            entity="subscriber",
            entity_id=sub.id,
        )
        if notifier.send_email(db, msg):
            sent += 1
            subscriber_hits.append(
                {"subscriber_id": sub.id, "days_left": days_left}
            )

    return JobReport(
        items_processed=len(advertiser_hits) + len(subscriber_hits),
        notifications_sent=sent,
        details={
            "advertiser_reminders": advertiser_hits,
            "subscriber_reminders": subscriber_hits,
            "windows": list(REMINDER_WINDOWS_DAYS),
            "provider": notifier.name,
        },
    )
