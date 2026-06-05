"""Glue between the Advertiser model and the deterministic churn engine."""
from datetime import datetime, timezone

from app.engines.churn import score_churn
from app.models.advertiser import Advertiser, ContractStatus


def days_to_active_contract_expiry(adv: Advertiser) -> int | None:
    today = datetime.now(timezone.utc).date()
    active = [
        c
        for c in adv.contracts
        if c.status == ContractStatus.ACTIVE and c.end_date is not None
    ]
    if not active:
        return None
    soonest = min(active, key=lambda c: c.end_date)
    return (soonest.end_date - today).days


def recompute_churn(adv: Advertiser) -> Advertiser:
    """Recompute and cache churn snapshot on the advertiser. Caller commits."""
    result = score_churn(
        spend_trend=float(adv.spend_trend or 0),
        open_rate=float(adv.proposal_open_rate or 0),
        days_to_expiry=days_to_active_contract_expiry(adv),
    )
    adv.churn_score = result.score
    adv.churn_band = result.band
    adv.churn_updated_at = datetime.now(timezone.utc)
    return adv
