"""Complaints API tests.

We run with no OPENROUTER_API_KEY in CI, so the triage endpoint exercises
the deterministic fallback path. The hard-rule (billing -> escalated) holds
regardless of AI.
"""


def _create(client, headers, **over) -> dict:
    body = {
        "subscriber_name": "Test Reader",
        "subscriber_phone": "+919000000010",
        "area": "Patan",
        "text": "Paper not delivered today.",
        "channel": "PHONE",
        **over,
    }
    r = client.post("/complaints", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_list_complaint(client, admin_headers) -> None:
    c = _create(client, admin_headers)
    assert c["triage"] == "PENDING"
    assert c["status"] == "OPEN"

    r = client.get("/complaints", headers=admin_headers)
    assert r.status_code == 200
    assert any(x["id"] == c["id"] for x in r.json())


def test_routine_triage_auto_resolves_via_engine_fallback(client, admin_headers) -> None:
    c = _create(client, admin_headers, text="Please pause my subscription for two weeks.")
    r = client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["auto"] is True
    assert body["source"] in ("AI", "ENGINE")  # depends on env

    # complaint now resolved
    r = client.get(f"/complaints/{c['id']}", headers=admin_headers)
    detail = r.json()
    assert detail["triage"] == "AUTO"
    assert detail["status"] == "RESOLVED"


def test_billing_dispute_always_escalates(client, admin_headers) -> None:
    c = _create(
        client,
        admin_headers,
        text="You charged me twice this month, this is a billing dispute, refund please.",
    )
    r = client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["auto"] is False
    # The sensitive-keyword guard fires before AI even runs, so source=ENGINE.
    assert body["source"] == "ENGINE"

    r = client.get(f"/complaints/{c['id']}", headers=admin_headers)
    detail = r.json()
    assert detail["triage"] == "ESCALATED"
    assert detail["status"] == "OPEN"  # NOT auto-resolved
    assert detail["resolution"] is None


def test_cannot_triage_resolved_complaint(client, admin_headers) -> None:
    c = _create(client, admin_headers, text="Pause subscription please.")
    client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)
    r = client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)
    assert r.status_code == 409


def test_assign_and_manual_resolve(client, admin_headers) -> None:
    # Create something that escalates
    c = _create(
        client,
        admin_headers,
        text="Reader is disputing the charge from last month.",
    )
    client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)

    # assign to current admin (id resolved from /auth/me)
    me = client.get("/auth/me", headers=admin_headers).json()
    r = client.post(
        f"/complaints/{c['id']}/assign",
        headers=admin_headers,
        json={"user_id": me["id"]},
    )
    assert r.status_code == 200
    assert r.json()["assigned_to_id"] == me["id"]

    # resolve manually
    r = client.post(
        f"/complaints/{c['id']}/resolve",
        headers=admin_headers,
        json={"resolution": "Refund approved after review of bank statements."},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVED"


def test_audit_log_written_for_triage(client, admin_headers) -> None:
    """Triage must write an AuditLog row with the right actor."""
    from app.core.db import SessionLocal
    from app.models.complaint import AuditLog

    c = _create(client, admin_headers, text="Please change my plan to weekend only.")
    client.post(f"/complaints/{c['id']}/triage", headers=admin_headers)

    with SessionLocal() as db:
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.entity == "complaint", AuditLog.entity_id == c["id"])
            .all()
        )
        actions = [r.action for r in rows]
        assert "create" in actions
        assert "triage" in actions
        triage_row = next(r for r in rows if r.action == "triage")
        assert triage_row.actor in ("AI",) or triage_row.actor.startswith("USER:")
        assert "source" in (triage_row.payload or {})
