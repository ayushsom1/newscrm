import uuid
from datetime import date, timedelta


def _unique_phone() -> str:
    return "+91" + uuid.uuid4().hex[:10]


def test_create_unique_phone_409(client, admin_headers) -> None:
    phone = _unique_phone()
    payload = {
        "name": "Anita Singh",
        "phone": phone,
        "area": "Patan",
        "plan": "DAILY",
    }
    r = client.post("/subscribers", headers=admin_headers, json=payload)
    assert r.status_code == 201, r.text

    r = client.post(
        "/subscribers",
        headers=admin_headers,
        json={**payload, "name": "Other Person"},
    )
    assert r.status_code == 409


def test_at_risk_filter_and_signal(client, admin_headers) -> None:
    r = client.post(
        "/subscribers",
        headers=admin_headers,
        json={
            "name": "Risky Reader",
            "phone": _unique_phone(),
            "area": "Patan",
            "plan": "DAILY",
            "missed_payments": 2,
        },
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert r.json()["renewal"]["at_risk"] is True
    assert r.json()["renewal"]["severity"] == "high"

    soon = date.today() + timedelta(days=3)
    r = client.post(
        f"/subscribers/{sid}/subscriptions",
        headers=admin_headers,
        json={
            "plan": "DAILY",
            "start_date": str(soon - timedelta(days=365)),
            "renew_date": str(soon),
            "monthly_price": "299.00",
        },
    )
    assert r.status_code == 201

    r = client.get(f"/subscribers/{sid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["renewal"]["at_risk"] is True
    assert len(r.json()["subscriptions"]) == 1

    r = client.get("/subscribers", headers=admin_headers, params={"at_risk": "true"})
    assert any(s["id"] == sid for s in r.json())


def test_forecast_groups_by_area(client, admin_headers) -> None:
    # ensure at least one active subscriber exists
    client.post(
        "/subscribers",
        headers=admin_headers,
        json={
            "name": "Forecast Seed",
            "phone": _unique_phone(),
            "area": "Patan",
            "plan": "DAILY",
        },
    )
    r = client.get("/subscribers/forecast", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_active"] >= 1
    assert body["total_target"] >= body["total_active"]
    areas = {a["area"] for a in body["areas"]}
    assert "Patan" in areas
