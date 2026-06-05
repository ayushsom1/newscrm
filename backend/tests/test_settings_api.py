import uuid


def _new_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def test_admin_can_create_user(client, admin_headers) -> None:
    email = _new_email()
    r = client.post(
        "/users",
        headers=admin_headers,
        json={
            "name": "New Reporter",
            "email": email,
            "role": "SALES",
            "password": "tempPass123",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "SALES"


def test_duplicate_email_returns_409(client, admin_headers) -> None:
    email = _new_email()
    r = client.post(
        "/users",
        headers=admin_headers,
        json={
            "name": "First",
            "email": email,
            "role": "SALES",
            "password": "tempPass123",
        },
    )
    assert r.status_code == 201
    r = client.post(
        "/users",
        headers=admin_headers,
        json={
            "name": "Second",
            "email": email,
            "role": "SALES",
            "password": "tempPass123",
        },
    )
    assert r.status_code == 409


def test_accounts_cannot_create_user(client, accounts_headers) -> None:
    r = client.post(
        "/users",
        headers=accounts_headers,
        json={
            "name": "X",
            "email": _new_email(),
            "role": "SALES",
            "password": "tempPass123",
        },
    )
    assert r.status_code == 403


def test_admin_cannot_demote_self(client, admin_headers) -> None:
    me = client.get("/auth/me", headers=admin_headers).json()
    r = client.patch(
        f"/users/{me['id']}",
        headers=admin_headers,
        json={"role": "SALES"},
    )
    assert r.status_code == 400


def test_admin_cannot_deactivate_self(client, admin_headers) -> None:
    me = client.get("/auth/me", headers=admin_headers).json()
    r = client.patch(
        f"/users/{me['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert r.status_code == 400


def test_admin_can_reset_password_and_user_can_login(client, admin_headers) -> None:
    email = _new_email()
    u = client.post(
        "/users",
        headers=admin_headers,
        json={
            "name": "Reset Test",
            "email": email,
            "role": "ACCOUNTS",
            "password": "oldPass123",
        },
    ).json()
    r = client.post(
        f"/users/{u['id']}/reset-password",
        headers=admin_headers,
        json={"new_password": "newPass456"},
    )
    assert r.status_code == 204
    # old password fails
    bad = client.post(
        "/auth/login", data={"username": email, "password": "oldPass123"}
    )
    assert bad.status_code == 401
    # new password works
    good = client.post(
        "/auth/login", data={"username": email, "password": "newPass456"}
    )
    assert good.status_code == 200


def test_get_and_update_autonomy(client, admin_headers) -> None:
    r = client.get("/settings/autonomy", headers=admin_headers)
    assert r.status_code == 200
    base = r.json()
    assert base["triage_ai_enabled"] is True
    assert base["ai_draft_enabled"] is True

    r = client.patch(
        "/settings/autonomy",
        headers=admin_headers,
        json={"triage_ai_enabled": False, "ai_draft_enabled": False},
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["triage_ai_enabled"] is False
    assert updated["ai_draft_enabled"] is False
    assert updated["updated_by_id"] is not None

    # restore for downstream tests
    client.patch(
        "/settings/autonomy",
        headers=admin_headers,
        json={"triage_ai_enabled": True, "ai_draft_enabled": True},
    )


def test_non_admin_cannot_update_autonomy(client, accounts_headers) -> None:
    r = client.patch(
        "/settings/autonomy",
        headers=accounts_headers,
        json={"triage_ai_enabled": False},
    )
    assert r.status_code == 403
