from datetime import date, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.jobs.runner import run_job
from app.jobs.tasks import (
    REMINDER_WINDOWS_DAYS,
    daily_expire_contracts,
    daily_renewal_reminders,
    nightly_churn_recompute,
)
from app.models.advertiser import (
    Advertiser,
    AdvertiserStatus,
    Contract,
    ContractStatus,
)
from app.models.job import JobRun, JobStatus
from app.models.subscriber import (
    Plan,
    Subscriber,
    SubscriberStatus,
    Subscription,
    SubscriptionStatus,
)


def _seed_advertiser(db, **k) -> Advertiser:
    a = Advertiser(
        name=k.pop("name", "Job Test Co"),
        category=k.pop("category", "Auto"),
        annual_value=k.pop("annual_value", 0),
        spend_trend=k.pop("spend_trend", -30),
        proposal_open_rate=k.pop("proposal_open_rate", 30),
        contact_email=k.pop("contact_email", "x@example.com"),
        status=k.pop("status", AdvertiserStatus.ACTIVE),
        **k,
    )
    db.add(a)
    db.flush()
    return a


def test_nightly_churn_recompute_writes_band_for_each_advertiser() -> None:
    with SessionLocal() as db:
        a = _seed_advertiser(db, name="Churn Job A", spend_trend=-80, proposal_open_rate=5)
        b = _seed_advertiser(db, name="Churn Job B", spend_trend=20, proposal_open_rate=80)
        db.commit()

        r = nightly_churn_recompute(db, date.today())
        db.commit()

        a = db.get(Advertiser, a.id)
        b = db.get(Advertiser, b.id)
        assert a.churn_band == "high"
        assert b.churn_band == "low"
        assert r.items_processed >= 2
        # bands count summed should equal items processed
        assert sum(r.details["bands"].values()) == r.items_processed


def test_daily_expire_contracts_marks_past_due() -> None:
    with SessionLocal() as db:
        a = _seed_advertiser(db, name="Expire Job Co")
        c = Contract(
            advertiser_id=a.id,
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=1),
            value=100000,
            slots=4,
            status=ContractStatus.ACTIVE,
        )
        db.add(c)
        db.commit()

        r = daily_expire_contracts(db, date.today())
        db.commit()

        db.refresh(c)
        assert c.status == ContractStatus.EXPIRED
        assert r.items_processed >= 1


def test_daily_renewal_reminders_targets_only_window_days() -> None:
    with SessionLocal() as db:
        # advertiser with contract ending in 7d (in window) and another in 21d (not)
        a1 = _seed_advertiser(db, name="Rem A1")
        a2 = _seed_advertiser(db, name="Rem A2")
        db.add(
            Contract(
                advertiser_id=a1.id,
                start_date=date.today() - timedelta(days=365),
                end_date=date.today() + timedelta(days=7),
                value=100000,
                slots=4,
                status=ContractStatus.ACTIVE,
            )
        )
        db.add(
            Contract(
                advertiser_id=a2.id,
                start_date=date.today() - timedelta(days=365),
                end_date=date.today() + timedelta(days=21),
                value=100000,
                slots=4,
                status=ContractStatus.ACTIVE,
            )
        )
        db.commit()

        r = daily_renewal_reminders(db, date.today())
        db.commit()

        hits = [h["advertiser_id"] for h in r.details["advertiser_reminders"]]
        assert a1.id in hits
        assert a2.id not in hits
        assert 7 in REMINDER_WINDOWS_DAYS


def test_run_job_is_idempotent_per_window() -> None:
    today = date.today()
    first = run_job("nightly_churn_recompute", window_date=today, triggered_by="TEST")
    second = run_job(
        "nightly_churn_recompute", window_date=today, triggered_by="TEST"
    )
    assert first.id == second.id  # second call returned the existing row

    with SessionLocal() as db:
        rows = db.scalars(
            select(JobRun).where(
                JobRun.job_name == "nightly_churn_recompute",
                JobRun.window_date == today,
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].status == JobStatus.SUCCESS
