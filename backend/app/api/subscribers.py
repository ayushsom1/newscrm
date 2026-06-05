from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.engines.printrun import forecast_print_run
from app.models.subscriber import (
    AreaReturns,
    Subscriber,
    SubscriberStatus,
    Subscription,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.schemas.subscriber import (
    AreaForecast,
    ForecastSummary,
    RenewalOut,
    SubscriberCreate,
    SubscriberDetail,
    SubscriberOut,
    SubscriberUpdate,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionUpdate,
)
from app.services.renewal import signal_for_subscriber

router = APIRouter(prefix="/subscribers", tags=["subscribers"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CIRCULATION)


def _serialize(sub: Subscriber) -> dict:
    signal, days = signal_for_subscriber(sub)
    return {
        "id": sub.id,
        "name": sub.name,
        "phone": sub.phone,
        "area": sub.area,
        "address": sub.address,
        "plan": sub.plan,
        "status": sub.status,
        "missed_payments": sub.missed_payments,
        "created_at": sub.created_at,
        "updated_at": sub.updated_at,
        "renewal": RenewalOut(
            at_risk=signal.at_risk,
            severity=signal.severity,
            reasons=signal.reasons,
            days_to_renew=days,
        ),
    }


@router.get("", response_model=list[SubscriberOut])
def list_subscribers(
    q: str | None = Query(default=None),
    area: str | None = Query(default=None),
    at_risk: bool | None = Query(default=None),
    status_filter: SubscriberStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    stmt = select(Subscriber).options(selectinload(Subscriber.subscriptions))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Subscriber.name.ilike(like), Subscriber.phone.ilike(like))
        )
    if area:
        stmt = stmt.where(Subscriber.area == area)
    if status_filter:
        stmt = stmt.where(Subscriber.status == status_filter)
    stmt = stmt.order_by(Subscriber.name).limit(limit).offset(offset)
    rows = list(db.scalars(stmt).all())
    serialized = [_serialize(s) for s in rows]
    if at_risk is not None:
        serialized = [s for s in serialized if s["renewal"].at_risk == at_risk]
    return serialized


@router.get("/forecast", response_model=ForecastSummary)
def forecast(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ForecastSummary:
    rows = db.execute(
        select(Subscriber.area, func.count(Subscriber.id))
        .where(Subscriber.status == SubscriberStatus.ACTIVE)
        .group_by(Subscriber.area)
        .order_by(Subscriber.area)
    ).all()
    returns_map = {r.area: float(r.returns_pct) for r in db.scalars(select(AreaReturns)).all()}

    areas: list[AreaForecast] = []
    total_target = 0
    total_active = 0
    for area, active in rows:
        rpct = returns_map.get(area, 0.0)
        result = forecast_print_run(active_subs=active, returns_pct=rpct)
        areas.append(
            AreaForecast(
                area=area,
                active_subs=active,
                newsstand_buffer=0,
                returns_pct=rpct,
                target=result.target,
            )
        )
        total_target += result.target
        total_active += active

    return ForecastSummary(
        total_target=total_target, total_active=total_active, areas=areas
    )


@router.get("/{subscriber_id}", response_model=SubscriberDetail)
def get_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    sub = db.get(Subscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    data = _serialize(sub)
    data["subscriptions"] = [SubscriptionOut.model_validate(s) for s in sub.subscriptions]
    return data


@router.post("", response_model=SubscriberOut, status_code=status.HTTP_201_CREATED)
def create_subscriber(
    payload: SubscriberCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    sub = Subscriber(**payload.model_dump())
    db.add(sub)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="phone already in use")
    db.refresh(sub)
    return _serialize(sub)


@router.patch("/{subscriber_id}", response_model=SubscriberOut)
def update_subscriber(
    subscriber_id: int,
    payload: SubscriberUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    sub = db.get(Subscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sub, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="phone already in use")
    db.refresh(sub)
    return _serialize(sub)


@router.delete("/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscriber(
    subscriber_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    sub = db.get(Subscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    db.delete(sub)
    db.commit()


# ---- subscriptions ----

@router.post(
    "/{subscriber_id}/subscriptions",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_subscription(
    subscriber_id: int,
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Subscription:
    sub = db.get(Subscriber, subscriber_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    if payload.renew_date < payload.start_date:
        raise HTTPException(status_code=400, detail="renew_date before start_date")
    s = Subscription(subscriber_id=sub.id, **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.patch(
    "/{subscriber_id}/subscriptions/{subscription_id}",
    response_model=SubscriptionOut,
)
def update_subscription(
    subscriber_id: int,
    subscription_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Subscription:
    s = db.get(Subscription, subscription_id)
    if s is None or s.subscriber_id != subscriber_id:
        raise HTTPException(status_code=404, detail="subscription not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    if s.renew_date < s.start_date:
        raise HTTPException(status_code=400, detail="renew_date before start_date")
    db.commit()
    db.refresh(s)
    return s


@router.delete(
    "/{subscriber_id}/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_subscription(
    subscriber_id: int,
    subscription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> None:
    s = db.get(Subscription, subscription_id)
    if s is None or s.subscriber_id != subscriber_id:
        raise HTTPException(status_code=404, detail="subscription not found")
    db.delete(s)
    db.commit()
