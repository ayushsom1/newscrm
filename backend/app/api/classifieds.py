from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.engines.pricing import quote as price_quote
from app.models.classified import Classified, ClassifiedStatus
from app.models.user import User, UserRole
from app.schemas.classified import (
    ClassifiedCreate,
    ClassifiedOut,
    QuoteIn,
    QuoteOut,
)

router = APIRouter(prefix="/classifieds", tags=["classifieds"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.SALES, UserRole.ACCOUNTS)


def _count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])


@router.post("/quote", response_model=QuoteOut)
def post_quote(
    payload: QuoteIn,
    _: User = Depends(get_current_user),
) -> QuoteOut:
    words = _count_words(payload.text)
    if words < 1:
        raise HTTPException(status_code=400, detail="text must contain at least one word")
    try:
        q = price_quote(
            words=words,
            category=payload.category,
            duration_days=payload.duration_days,
            locale=payload.locale,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return QuoteOut(
        currency=q.currency,
        tax_label=q.tax_label,
        word_count=words,
        net=q.net,
        tax=q.tax,
        total=q.total,
        breakdown=q.breakdown,
    )


@router.get("", response_model=list[ClassifiedOut])
def list_classifieds(
    q: str | None = Query(default=None),
    status_filter: ClassifiedStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Classified]:
    stmt = select(Classified)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Classified.customer_name.ilike(like),
                Classified.customer_phone.ilike(like),
                Classified.text.ilike(like),
            )
        )
    if status_filter:
        stmt = stmt.where(Classified.status == status_filter)
    stmt = stmt.order_by(Classified.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.get("/{classified_id}", response_model=ClassifiedOut)
def get_classified(
    classified_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Classified:
    c = db.get(Classified, classified_id)
    if c is None:
        raise HTTPException(status_code=404, detail="classified not found")
    return c


@router.post("", response_model=ClassifiedOut, status_code=status.HTTP_201_CREATED)
def create_classified(
    payload: ClassifiedCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Classified:
    words = _count_words(payload.text)
    if words < 1:
        raise HTTPException(status_code=400, detail="text must contain at least one word")
    try:
        q = price_quote(
            words=words,
            category=payload.category,
            duration_days=payload.duration_days,
            locale=payload.locale,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    c = Classified(
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        text=payload.text,
        word_count=words,
        category=payload.category.upper(),
        duration_days=payload.duration_days,
        locale=payload.locale,
        currency=q.currency,
        price_net=q.net,
        price_tax=q.tax,
        price_total=q.total,
        status=ClassifiedStatus.QUOTED,
        publish_date=payload.publish_date,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{classified_id}/mark-paid", response_model=ClassifiedOut)
def mark_paid(
    classified_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Classified:
    c = db.get(Classified, classified_id)
    if c is None:
        raise HTTPException(status_code=404, detail="classified not found")
    if c.status != ClassifiedStatus.QUOTED:
        raise HTTPException(
            status_code=409,
            detail=f"cannot mark-paid in status {c.status.value}",
        )
    c.status = ClassifiedStatus.PAID
    c.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{classified_id}/mark-published", response_model=ClassifiedOut)
def mark_published(
    classified_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Classified:
    c = db.get(Classified, classified_id)
    if c is None:
        raise HTTPException(status_code=404, detail="classified not found")
    if c.status != ClassifiedStatus.PAID:
        raise HTTPException(
            status_code=409,
            detail=f"cannot mark-published in status {c.status.value}",
        )
    c.status = ClassifiedStatus.PUBLISHED
    c.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.post("/{classified_id}/cancel", response_model=ClassifiedOut)
def cancel(
    classified_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.SALES)),
) -> Classified:
    c = db.get(Classified, classified_id)
    if c is None:
        raise HTTPException(status_code=404, detail="classified not found")
    if c.status == ClassifiedStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="already published")
    c.status = ClassifiedStatus.CANCELLED
    db.commit()
    db.refresh(c)
    return c
