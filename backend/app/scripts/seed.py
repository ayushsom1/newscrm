"""Seed dev data. Idempotent.

Run inside the backend container:
    python -m app.scripts.seed
"""
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


SEED_USERS = [
    ("Admin", "admin@example.com", "admin123", UserRole.ADMIN),
    ("Sales Lead", "sales@example.com", "sales123", UserRole.SALES),
    ("Circulation", "circ@example.com", "circ123", UserRole.CIRCULATION),
    ("Accounts", "accounts@example.com", "accounts123", UserRole.ACCOUNTS),
]


def run() -> None:
    with SessionLocal() as db:
        for name, email, password, role in SEED_USERS:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                continue
            db.add(
                User(
                    name=name,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
        db.commit()
    print("seed: done")


if __name__ == "__main__":
    run()
