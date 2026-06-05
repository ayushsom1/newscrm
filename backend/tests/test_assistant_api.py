"""Assistant tests with AI mocked.

We assert: persistence (conversation + messages), proposed-action whitelist,
approve/reject flow, and that approve triggers the right domain mutation.
The actual model call is replaced with a deterministic stub.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

import app.ai.assistant as assistant_mod
from app.ai.client import ChatResult


def _stub_chat_factory(reply_text: str, tool_calls: list[dict[str, Any]] | None = None):
    def _stub(**kwargs):
        return ChatResult(
            model="stub/mock-model",
            content=reply_text,
            usage=None,
            raw={},
            tool_calls=tool_calls,
        )
    return _stub


@pytest.fixture
def stub_text_only(monkeypatch):
    monkeypatch.setattr(
        assistant_mod,
        "chat_messages",
        _stub_chat_factory("You have 0 advertisers active today."),
    )


@pytest.fixture
def stub_with_renewal_tool(monkeypatch):
    def _stub(advertiser_id: int):
        monkeypatch.setattr(
            assistant_mod,
            "chat_messages",
            _stub_chat_factory(
                "Suggest drafting a renewal for the at-risk advertiser.",
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "propose_renewal_draft",
                            "arguments": json.dumps(
                                {
                                    "advertiser_id": advertiser_id,
                                    "rationale": "Spend is down and contract expires soon.",
                                }
                            ),
                        },
                    }
                ],
            ),
        )
    return _stub


def test_chat_persists_messages_and_returns_text(client, admin_headers, stub_text_only) -> None:
    r = client.post(
        "/ai/chat",
        headers=admin_headers,
        json={"message": "How many advertisers are active?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    cid = body["conversation_id"]
    assert body["assistant_text"]
    assert body["proposed_actions"] == []

    detail = client.get(f"/conversations/{cid}", headers=admin_headers).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["USER", "ASSISTANT"]


def test_chat_tool_call_persisted_as_proposed_action(
    client, admin_headers, stub_with_renewal_tool
) -> None:
    # Create an advertiser the assistant can reference.
    adv = client.post(
        "/advertisers",
        headers=admin_headers,
        json={"name": "Asst Test Co", "spend_trend": "-30", "proposal_open_rate": "20"},
    ).json()
    stub_with_renewal_tool(adv["id"])

    r = client.post(
        "/ai/chat",
        headers=admin_headers,
        json={"message": "Who should I draft renewals for?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["proposed_actions"]) == 1
    pa = body["proposed_actions"][0]
    assert pa["tool_name"] == "propose_renewal_draft"
    assert pa["status"] == "PENDING"
    assert pa["arguments"]["advertiser_id"] == adv["id"]


def test_approving_a_renewal_proposal_creates_a_draft_proposal(
    client, admin_headers, stub_with_renewal_tool, monkeypatch
) -> None:
    # Force the drafter into engine fallback for determinism.
    import app.ai.drafter as drafter
    from app.ai.client import AIDisabledError

    def _raise(*a, **kw):
        raise AIDisabledError("disabled in tests")

    monkeypatch.setattr(drafter, "chat", _raise)

    adv = client.post(
        "/advertisers",
        headers=admin_headers,
        json={"name": "Approve Co", "spend_trend": "0", "proposal_open_rate": "50"},
    ).json()
    stub_with_renewal_tool(adv["id"])

    chat_r = client.post(
        "/ai/chat",
        headers=admin_headers,
        json={"message": "Draft renewal for Approve Co"},
    ).json()
    action_id = chat_r["proposed_actions"][0]["id"]

    r = client.post(
        f"/proposed-actions/{action_id}/approve", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "EXECUTED"
    assert "proposal_id" in body["result"]

    # And a real Proposal row exists.
    proposals = client.get(
        f"/advertisers/{adv['id']}/proposals", headers=admin_headers
    ).json()
    assert any(p["id"] == body["result"]["proposal_id"] for p in proposals)


def test_reject_proposed_action(
    client, admin_headers, stub_with_renewal_tool
) -> None:
    adv = client.post(
        "/advertisers",
        headers=admin_headers,
        json={"name": "Reject Co", "spend_trend": "0", "proposal_open_rate": "50"},
    ).json()
    stub_with_renewal_tool(adv["id"])

    chat_r = client.post(
        "/ai/chat",
        headers=admin_headers,
        json={"message": "Draft renewal for Reject Co"},
    ).json()
    action_id = chat_r["proposed_actions"][0]["id"]

    r = client.post(
        f"/proposed-actions/{action_id}/reject", headers=admin_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"

    # Cannot approve afterwards.
    r = client.post(
        f"/proposed-actions/{action_id}/approve", headers=admin_headers
    )
    assert r.status_code == 409


def test_unknown_tool_is_dropped_not_persisted(client, admin_headers, monkeypatch) -> None:
    monkeypatch.setattr(
        assistant_mod,
        "chat_messages",
        _stub_chat_factory(
            "Trying a sneaky tool.",
            tool_calls=[
                {
                    "id": "call_x",
                    "type": "function",
                    "function": {
                        "name": "delete_everything",
                        "arguments": "{}",
                    },
                }
            ],
        ),
    )
    r = client.post(
        "/ai/chat",
        headers=admin_headers,
        json={"message": "Hi"},
    )
    assert r.status_code == 200
    assert r.json()["proposed_actions"] == []


def test_other_user_cannot_see_conversation(
    client, admin_headers, accounts_headers, stub_text_only
) -> None:
    r = client.post(
        "/ai/chat", headers=admin_headers, json={"message": "First message"}
    ).json()
    cid = r["conversation_id"]
    r = client.get(f"/conversations/{cid}", headers=accounts_headers)
    assert r.status_code == 404
