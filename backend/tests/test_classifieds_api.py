from decimal import Decimal


def test_quote_endpoint_no_persist(client, admin_headers) -> None:
    r = client.post(
        "/classifieds/quote",
        headers=admin_headers,
        json={
            "text": "Two bedroom flat for rent in Patan road, sunny balcony.",
            "category": "PROPERTY",
            "duration_days": 7,
            "locale": "IN",
        },
    )
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["currency"] == "INR"
    assert q["tax_label"] == "GST"
    assert q["word_count"] >= 8
    assert Decimal(q["total"]) > Decimal(q["net"])


def test_booking_locks_in_price_and_status_flow(client, admin_headers) -> None:
    r = client.post(
        "/classifieds",
        headers=admin_headers,
        json={
            "customer_name": "Priya Sharma",
            "customer_phone": "+919876543210",
            "text": "Lost a black wallet near central park, contact owner.",
            "category": "GENERAL",
            "duration_days": 3,
            "locale": "IN",
        },
    )
    assert r.status_code == 201, r.text
    c = r.json()
    cid = c["id"]
    assert c["status"] == "QUOTED"
    locked_total = c["price_total"]

    # quote -> paid
    r = client.post(f"/classifieds/{cid}/mark-paid", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "PAID"
    assert r.json()["price_total"] == locked_total  # price didn't drift

    # double mark-paid -> 409
    r = client.post(f"/classifieds/{cid}/mark-paid", headers=admin_headers)
    assert r.status_code == 409

    # paid -> published
    r = client.post(f"/classifieds/{cid}/mark-published", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "PUBLISHED"

    # cannot cancel after publish
    r = client.post(f"/classifieds/{cid}/cancel", headers=admin_headers)
    assert r.status_code == 409


def test_invalid_category_rejected(client, admin_headers) -> None:
    r = client.post(
        "/classifieds/quote",
        headers=admin_headers,
        json={
            "text": "Some ad text here.",
            "category": "ALIENS",
            "duration_days": 1,
            "locale": "IN",
        },
    )
    assert r.status_code == 400


def test_nepal_locale_quote_uses_npr(client, admin_headers) -> None:
    r = client.post(
        "/classifieds/quote",
        headers=admin_headers,
        json={
            "text": "घर भाडामा चाहिएको छ, काठमाडौंमा।",
            "category": "PROPERTY",
            "duration_days": 1,
            "locale": "NP",
        },
    )
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["currency"] == "NPR"
    assert q["tax_label"] == "VAT"
