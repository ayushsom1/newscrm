"""Proposals API tests.

Runs with whatever OPENROUTER_API_KEY is in the env. If the model is reachable,
the draft body will look like real prose; otherwise the deterministic engine
template is used. Either way, status/needs_human/audit semantics must hold.
"""
from datetime import date, timedelta

import pytest

from app.ai.client import AIDisabledError


@pytest.fixture(autouse=True)
def _force_ai_engine_fallback(monkeypatch):
    """Make every proposal test exercise the engine fallback path — no live
    network, deterministic body. We have separate triage tests that already
    cover the AI path."""
    import app.ai.drafter as drafter

    def _raise(*a, **kw):
        raise AIDisabledError("disabled in tests")

    monkeypatch.setattr(drafter, "chat", _raise)
    yield


def _make_advertiser(client, headers, **over) -> dict:
    body = {
        "name": "Proposal Co",
        "category": "Auto",
        "annual_value": "500000.00",
        "spend_trend": "0",
        "proposal_open_rate": "60",
        "status": "ACTIVE",
        **over,
    }
    r = client.post("/advertisers", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_ai_draft_creates_draft_status_proposal(client, admin_headers) -> None:
    adv = _make_advertiser(client, admin_headers, name="Acme Renewals")
    r = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=admin_headers
    )
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["status"] == "DRAFT"
    assert p["source"] == "AI_DRAFT"
    assert p["subject"]
    assert p["body"]
    assert p["created_by_id"] is not None
    assert p["approved_at"] is None


def test_high_churn_proposal_is_flagged_needs_human(client, admin_headers) -> None:
    adv = _make_advertiser(
        client,
        admin_headers,
        name="Risky Renewal",
        spend_trend="-80",
        proposal_open_rate="5",
    )
    # add an expiring contract to push band to high
    soon = date.today() + timedelta(days=3)
    client.post(
        f"/advertisers/{adv['id']}/contracts",
        headers=admin_headers,
        json={
            "start_date": str(soon - timedelta(days=365)),
            "end_date": str(soon),
            "value": "100000.00",
            "slots": 4,
        },
    )
    r = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=admin_headers
    )
    assert r.status_code == 201
    p = r.json()
    assert p["needs_human"] is True
    assert p["needs_human_reason"]


def test_approval_flow_draft_to_approved_to_sent(client, admin_headers) -> None:
    adv = _make_advertiser(client, admin_headers, name="Send Co")
    p = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=admin_headers
    ).json()
    pid = p["id"]

    # cannot send before approve
    r = client.post(f"/proposals/{pid}/send", headers=admin_headers)
    assert r.status_code == 409

    # approve
    r = client.post(f"/proposals/{pid}/approve", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"
    assert r.json()["approved_by_id"] is not None

    # cannot approve again
    r = client.post(f"/proposals/{pid}/approve", headers=admin_headers)
    assert r.status_code == 409

    # send
    r = client.post(f"/proposals/{pid}/send", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "SENT"
    assert r.json()["sent_at"] is not None


def test_reject_blocks_send(client, admin_headers) -> None:
    adv = _make_advertiser(client, admin_headers, name="Reject Co")
    p = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=admin_headers
    ).json()
    pid = p["id"]
    assert client.post(f"/proposals/{pid}/reject", headers=admin_headers).status_code == 200
    r = client.post(f"/proposals/{pid}/send", headers=admin_headers)
    assert r.status_code == 409


def test_accounts_role_cannot_draft(client, admin_headers, accounts_headers) -> None:
    adv = _make_advertiser(client, admin_headers, name="Accounts Block Co")
    r = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=accounts_headers
    )
    assert r.status_code == 403


def test_audit_log_records_ai_draft_actor(client, admin_headers) -> None:
    from app.core.db import SessionLocal
    from app.models.complaint import AuditLog

    adv = _make_advertiser(client, admin_headers, name="Audit Co")
    p = client.post(
        f"/advertisers/{adv['id']}/proposals/draft", headers=admin_headers
    ).json()

    with SessionLocal() as db:
        rows = (
            db.query(AuditLog)
            .filter(AuditLog.entity == "proposal", AuditLog.entity_id == p["id"])
            .all()
        )
        actions = [r.action for r in rows]
        assert "draft" in actions
        draft_row = next(r for r in rows if r.action == "draft")
        assert draft_row.actor == "AI"
        assert "model" in (draft_row.payload or {})


def test_human_proposal_is_not_flagged_needs_human(client, admin_headers) -> None:
    adv = _make_advertiser(client, admin_headers, name="Human Wrote It Co")
    r = client.post(
        f"/advertisers/{adv['id']}/proposals",
        headers=admin_headers,
        json={"subject": "Custom subject", "body": "Hand-written proposal body."},
    )
    assert r.status_code == 201
    p = r.json()
    assert p["source"] == "HUMAN"
    assert p["needs_human"] is False
