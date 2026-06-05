from datetime import date, timedelta


def test_create_list_get_update_delete(client, admin_headers) -> None:
    # create
    r = client.post(
        "/advertisers",
        headers=admin_headers,
        json={
            "name": "Acme Motors",
            "category": "Auto",
            "annual_value": "1200000.00",
            "spend_trend": "-25.0",
            "proposal_open_rate": "15.0",
            "status": "ACTIVE",
        },
    )
    assert r.status_code == 201, r.text
    adv = r.json()
    aid = adv["id"]
    assert adv["churn"]["band"] in ("low", "med", "high")
    assert adv["churn"]["score"] is not None

    # list (search)
    r = client.get("/advertisers", headers=admin_headers, params={"q": "Acme"})
    assert r.status_code == 200
    assert any(a["id"] == aid for a in r.json())

    # get
    r = client.get(f"/advertisers/{aid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["contracts"] == []

    # update -> churn recomputed
    r = client.patch(
        f"/advertisers/{aid}",
        headers=admin_headers,
        json={"spend_trend": "50.0", "proposal_open_rate": "80.0"},
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["churn"]["band"] == "low"

    # delete
    r = client.delete(f"/advertisers/{aid}", headers=admin_headers)
    assert r.status_code == 204
    r = client.get(f"/advertisers/{aid}", headers=admin_headers)
    assert r.status_code == 404


def test_rbac_accounts_cannot_write(client, admin_headers, accounts_headers) -> None:
    r = client.post(
        "/advertisers",
        headers=accounts_headers,
        json={"name": "Should Fail"},
    )
    assert r.status_code == 403

    # but accounts can read
    r = client.get("/advertisers", headers=accounts_headers)
    assert r.status_code == 200


def test_contracts_lifecycle_recomputes_churn(client, admin_headers) -> None:
    r = client.post(
        "/advertisers",
        headers=admin_headers,
        json={"name": "Bharat Bazaar", "spend_trend": "0", "proposal_open_rate": "50"},
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    baseline_band = r.json()["churn"]["band"]

    # contract expiring in 5 days should raise risk
    soon = date.today() + timedelta(days=5)
    r = client.post(
        f"/advertisers/{aid}/contracts",
        headers=admin_headers,
        json={
            "start_date": str(soon - timedelta(days=365)),
            "end_date": str(soon),
            "value": "100000.00",
            "slots": 4,
        },
    )
    assert r.status_code == 201, r.text

    r = client.get(f"/advertisers/{aid}", headers=admin_headers)
    detail = r.json()
    assert len(detail["contracts"]) == 1
    # band should be at-or-worse than baseline; expiring contract bumps score
    band_order = ["low", "med", "high"]
    assert band_order.index(detail["churn"]["band"]) >= band_order.index(baseline_band)

    # invalid contract (end before start) -> 400
    r = client.post(
        f"/advertisers/{aid}/contracts",
        headers=admin_headers,
        json={
            "start_date": str(date.today()),
            "end_date": str(date.today() - timedelta(days=1)),
            "value": "10",
        },
    )
    assert r.status_code == 400
