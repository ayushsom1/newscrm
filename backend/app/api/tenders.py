from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.models.tender import GovTender, TenderStatus
from app.models.user import User, UserRole
from app.schemas.tender import TenderCreate, TenderOut, TenderUpdate

router = APIRouter(prefix="/tenders", tags=["tenders"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.SALES)


@router.get("", response_model=list[TenderOut])
def list_tenders(
    status_filter: TenderStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[GovTender]:
    stmt = select(GovTender).order_by(GovTender.deadline).limit(limit)
    if status_filter:
        stmt = stmt.where(GovTender.status == status_filter)
    return list(db.scalars(stmt).all())


@router.post("", response_model=TenderOut, status_code=status.HTTP_201_CREATED)
def create_tender(
    payload: TenderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> GovTender:
    t = GovTender(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{tender_id}", response_model=TenderOut)
def update_tender(
    tender_id: int,
    payload: TenderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> GovTender:
    t = db.get(GovTender, tender_id)
    if t is None:
        raise HTTPException(status_code=404, detail="tender not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tender(
    tender_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    t = db.get(GovTender, tender_id)
    if t is None:
        raise HTTPException(status_code=404, detail="tender not found")
    db.delete(t)
    db.commit()
