from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole

client = TestClient(app)


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


def _token(email: str, password: str) -> str:
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_and_me() -> None:
    email = "admin@example.com"
    _ensure_user(email, "admin123", UserRole.ADMIN)
    token = _token(email, "admin123")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "ADMIN"


def test_bad_password_401() -> None:
    email = "admin@example.com"
    _ensure_user(email, "admin123", UserRole.ADMIN)
    r = client.post("/auth/login", data={"username": email, "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token() -> None:
    r = client.get("/auth/me")
    assert r.status_code == 401
