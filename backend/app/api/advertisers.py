from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.engines.churn import score_churn
from app.models.advertiser import (
    Advertiser,
    AdvertiserStatus,
    Contract,
)
from app.models.user import User, UserRole
from app.schemas.advertiser import (
    AdvertiserCreate,
    AdvertiserDetail,
    AdvertiserOut,
    AdvertiserUpdate,
    ChurnOut,
    ContractCreate,
    ContractOut,
    ContractUpdate,
)
from app.services.churn import days_to_active_contract_expiry, recompute_churn

router = APIRouter(prefix="/advertisers", tags=["advertisers"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.SALES)


def _serialize(adv: Advertiser) -> dict:
    return {
        "id": adv.id,
        "name": adv.name,
        "category": adv.category,
        "contact_name": adv.contact_name,
        "contact_phone": adv.contact_phone,
        "contact_email": adv.contact_email,
        "annual_value": adv.annual_value,
        "spend_trend": adv.spend_trend,
        "proposal_open_rate": adv.proposal_open_rate,
        "status": adv.status,
        "created_at": adv.created_at,
        "updated_at": adv.updated_at,
        "churn": ChurnOut(
            score=adv.churn_score,
            band=adv.churn_band,
            reasons=score_churn(
                float(adv.spend_trend or 0),
                float(adv.proposal_open_rate or 0),
                days_to_active_contract_expiry(adv),
            ).reasons,
            updated_at=adv.churn_updated_at,
        ),
    }


@router.get("", response_model=list[AdvertiserOut])
def list_advertisers(
    q: str | None = Query(default=None),
    status_filter: AdvertiserStatus | None = Query(default=None, alias="status"),
    band: str | None = Query(default=None, pattern="^(low|med|high)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    stmt = select(Advertiser).options(selectinload(Advertiser.contracts))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Advertiser.name.ilike(like), Advertiser.category.ilike(like))
        )
    if status_filter:
        stmt = stmt.where(Advertiser.status == status_filter)
    if band:
        stmt = stmt.where(Advertiser.churn_band == band)
    stmt = stmt.order_by(Advertiser.name).limit(limit).offset(offset)
    rows = db.scalars(stmt).all()
    return [_serialize(a) for a in rows]


@router.get("/{advertiser_id}", response_model=AdvertiserDetail)
def get_advertiser(
    advertiser_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    adv = db.get(Advertiser, advertiser_id)
    if adv is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    data = _serialize(adv)
    data["contracts"] = [ContractOut.model_validate(c) for c in adv.contracts]
    return data


@router.post("", response_model=AdvertiserOut, status_code=status.HTTP_201_CREATED)
def create_advertiser(
    payload: AdvertiserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    adv = Advertiser(**payload.model_dump())
    db.add(adv)
    db.flush()
    recompute_churn(adv)
    db.commit()
    db.refresh(adv)
    return _serialize(adv)


@router.patch("/{advertiser_id}", response_model=AdvertiserOut)
def update_advertiser(
    advertiser_id: int,
    payload: AdvertiserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    adv = db.get(Advertiser, advertiser_id)
    if adv is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(adv, k, v)
    recompute_churn(adv)
    db.commit()
    db.refresh(adv)
    return _serialize(adv)


@router.delete("/{advertiser_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_advertiser(
    advertiser_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    adv = db.get(Advertiser, advertiser_id)
    if adv is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    db.delete(adv)
    db.commit()


# ---- contracts ----

@router.post(
    "/{advertiser_id}/contracts",
    response_model=ContractOut,
    status_code=status.HTTP_201_CREATED,
)
def add_contract(
    advertiser_id: int,
    payload: ContractCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Contract:
    adv = db.get(Advertiser, advertiser_id)
    if adv is None:
        raise HTTPException(status_code=404, detail="advertiser not found")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date before start_date")
    contract = Contract(advertiser_id=adv.id, **payload.model_dump())
    db.add(contract)
    db.flush()
    db.refresh(adv)
    recompute_churn(adv)
    db.commit()
    db.refresh(contract)
    return contract


@router.patch(
    "/{advertiser_id}/contracts/{contract_id}", response_model=ContractOut
)
def update_contract(
    advertiser_id: int,
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None or contract.advertiser_id != advertiser_id:
        raise HTTPException(status_code=404, detail="contract not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(contract, k, v)
    if contract.end_date < contract.start_date:
        raise HTTPException(status_code=400, detail="end_date before start_date")
    db.flush()
    adv = db.get(Advertiser, advertiser_id)
    if adv is not None:
        db.refresh(adv)
        recompute_churn(adv)
    db.commit()
    db.refresh(contract)
    return contract


@router.delete(
    "/{advertiser_id}/contracts/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contract(
    advertiser_id: int,
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*WRITE_ROLES)),
) -> None:
    contract = db.get(Contract, contract_id)
    if contract is None or contract.advertiser_id != advertiser_id:
        raise HTTPException(status_code=404, detail="contract not found")
    db.delete(contract)
    db.flush()
    adv = db.get(Advertiser, advertiser_id)
    if adv is not None:
        db.refresh(adv)
        recompute_churn(adv)
    db.commit()
