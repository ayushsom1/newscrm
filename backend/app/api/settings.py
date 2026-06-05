from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.models.settings import SINGLETON_ID, AutonomyConfig
from app.models.user import User, UserRole
from app.schemas.autonomy import AutonomyOut, AutonomyUpdate
from app.services.audit import write_audit
from app.services.autonomy import invalidate_cache

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> AutonomyConfig:
    row = db.get(AutonomyConfig, SINGLETON_ID)
    if row is None:
        row = AutonomyConfig(id=SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/autonomy", response_model=AutonomyOut)
def get_autonomy(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AutonomyConfig:
    return _get_or_create(db)


@router.patch("/autonomy", response_model=AutonomyOut)
def update_autonomy(
    payload: AutonomyUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> AutonomyConfig:
    row = _get_or_create(db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_by_id = actor.id
    write_audit(
        db,
        actor=actor,
        action="update_autonomy",
        entity="autonomy_config",
        entity_id=row.id,
        payload=data,
    )
    db.commit()
    db.refresh(row)
    invalidate_cache()
    return row
