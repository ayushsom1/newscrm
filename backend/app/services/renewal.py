"""Glue between Subscriber model and the renewal engine."""
from datetime import datetime, timezone

from app.engines.renewal import RenewalSignal, evaluate_renewal
from app.models.subscriber import Subscriber, SubscriptionStatus


def days_to_next_renewal(sub: Subscriber) -> int | None:
    today = datetime.now(timezone.utc).date()
    active = [
        s for s in sub.subscriptions if s.status == SubscriptionStatus.ACTIVE
    ]
    if not active:
        return None
    soonest = min(active, key=lambda s: s.renew_date)
    return (soonest.renew_date - today).days


def signal_for_subscriber(sub: Subscriber) -> tuple[RenewalSignal, int | None]:
    days = days_to_next_renewal(sub)
    signal = evaluate_renewal(
        days_to_renew=days if days is not None else 9999,
        missed_payments=sub.missed_payments or 0,
    )
    return signal, days
