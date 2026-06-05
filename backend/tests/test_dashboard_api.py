from datetime import date, timedelta


def test_kpis_has_blocks_and_revenue(client, admin_headers) -> None:
    r = client.get("/dashboard/kpis", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    labels = [b["label"] for b in body["blocks"]]
    assert "Active advertisers" in labels
    assert "Active subscribers" in labels
    assert "Open complaints" in labels
    assert "Proposals pending approval" in labels
    assert isinstance(body["revenue_running_total_inr"], str)


def test_exception_queue_includes_expiring_contract(client, admin_headers) -> None:
    # arrange: an advertiser with a contract expiring in 5 days -> APPROVE
    adv = client.post(
        "/advertisers",
        headers=admin_headers,
        json={"name": "Dash Co", "spend_trend": "0", "proposal_open_rate": "50"},
    ).json()
    soon = date.today() + timedelta(days=5)
    r = client.post(
        f"/advertisers/{adv['id']}/contracts",
        headers=admin_headers,
        json={
            "start_date": str(soon - timedelta(days=365)),
            "end_date": str(soon),
            "value": "100000",
            "slots": 4,
        },
    )
    assert r.status_code == 201

    r = client.get("/dashboard/exception-queue", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    types = [i["type"] for i in body["items"]]
    assert "contract_expiry" in types
    assert body["counts"]["APPROVE"] >= 1


def test_tender_within_14d_appears_in_queue(client, admin_headers) -> None:
    r = client.post(
        "/tenders",
        headers=admin_headers,
        json={
            "title": "Public Health Campaign",
            "department": "Ministry of Health",
            "deadline": str(date.today() + timedelta(days=10)),
            "est_value": "300000",
            "status": "OPEN",
        },
    )
    assert r.status_code == 201
    q = client.get("/dashboard/exception-queue", headers=admin_headers).json()
    assert any(i["type"] == "tender_deadline" for i in q["items"])


def test_accounts_role_can_read_dashboard(client, accounts_headers) -> None:
    # read-only role should still see the dashboard
    r = client.get("/dashboard/kpis", headers=accounts_headers)
    assert r.status_code == 200
