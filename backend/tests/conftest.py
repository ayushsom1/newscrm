from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole


def _ensure_user(email: str, password: str, role: UserRole) -> None:
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            db.add(
                User(
                    name=email.split("@")[0],
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            db.commit()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _token(client: TestClient, email: str, password: str) -> str:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(client: TestClient) -> dict[str, str]:
    _ensure_user("admin@example.com", "admin123", UserRole.ADMIN)
    return {"Authorization": f"Bearer {_token(client, 'admin@example.com', 'admin123')}"}


@pytest.fixture(scope="session")
def accounts_headers(client: TestClient) -> dict[str, str]:
    _ensure_user("accounts@example.com", "accounts123", UserRole.ACCOUNTS)
    return {
        "Authorization": f"Bearer {_token(client, 'accounts@example.com', 'accounts123')}"
    }
