from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.users import (
    PasswordResetBody,
    UserCreate,
    UserDetail,
    UserUpdate,
)
from app.services.audit import write_audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserDetail])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.name)).all())


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    u = User(
        name=payload.name,
        email=payload.email.lower(),
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already in use")
    write_audit(
        db,
        actor=actor,
        action="create_user",
        entity="user",
        entity_id=u.id,
        payload={"email": u.email, "role": u.role.value},
    )
    db.commit()
    db.refresh(u)
    return u


@router.patch("/{user_id}", response_model=UserDetail)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    data = payload.model_dump(exclude_unset=True)
    # Don't let an admin deactivate or demote themselves — lockout hazard.
    if u.id == actor.id:
        if data.get("is_active") is False:
            raise HTTPException(
                status_code=400, detail="cannot deactivate your own account"
            )
        if "role" in data and data["role"] != UserRole.ADMIN:
            raise HTTPException(
                status_code=400, detail="cannot demote your own admin role"
            )
    for k, v in data.items():
        setattr(u, k, v)
    write_audit(
        db,
        actor=actor,
        action="update_user",
        entity="user",
        entity_id=u.id,
        payload=data,
    )
    db.commit()
    db.refresh(u)
    return u


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    body: PasswordResetBody,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    u.password_hash = hash_password(body.new_password)
    write_audit(
        db,
        actor=actor,
        action="reset_password",
        entity="user",
        entity_id=u.id,
    )
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    if u.id == actor.id:
        raise HTTPException(
            status_code=400, detail="cannot delete your own account"
        )
    db.delete(u)
    write_audit(
        db,
        actor=actor,
        action="delete_user",
        entity="user",
        entity_id=user_id,
    )
    db.commit()
