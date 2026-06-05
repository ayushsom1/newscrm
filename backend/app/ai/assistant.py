"""Grounded CRM assistant.

Design:
  * We expose a small, deliberate set of "propose_*" tools to the model.
  * The model can suggest exactly one or more proposed actions per turn,
    but we NEVER execute them. They land in proposed_actions as PENDING,
    a human approves/rejects in the UI, and approval routes through the
    same domain endpoints as everywhere else.
  * Grounding: a compact, read-only CRM snapshot is injected into the
    system prompt every turn.
  * No tool, ever, mutates the database directly from this module.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.ai.client import AIClientError, AIDisabledError, ChatResult, chat_messages
from app.ai.snapshot import build_crm_snapshot
from app.models.assistant import (
    Conversation,
    Message,
    MessageRole,
    ProposedAction,
    ProposedActionStatus,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool spec (OpenAI-compatible). Each tool is "propose_*" — the assistant
# can only PROPOSE; humans approve.
# ---------------------------------------------------------------------------
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_renewal_draft",
            "description": (
                "Propose drafting a renewal/sales proposal for one advertiser. "
                "When the user approves, the existing AI drafter will write "
                "the body; a human still reviews before send."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "advertiser_id": {
                        "type": "integer",
                        "description": "Advertiser ID from the snapshot.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this advertiser, in 1-2 sentences.",
                    },
                },
                "required": ["advertiser_id", "rationale"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_send_renewal_reminder",
            "description": (
                "Propose sending a polite renewal-reminder email to a "
                "subscriber whose subscription is at risk."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subscriber_id": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["subscriber_id", "rationale"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_assign_complaint",
            "description": (
                "Propose assigning an escalated complaint to a specific user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_id": {"type": "integer"},
                    "assignee_user_id": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["complaint_id", "assignee_user_id", "rationale"],
            },
        },
    },
]


SYSTEM_PROMPT = """You are the in-house assistant for a regional newspaper CRM.

You have a read-only SNAPSHOT of the CRM at the start of every turn. Use it
to answer questions and to propose specific, narrow actions.

Hard rules:
- Numbers (counts, money, dates) come ONLY from the snapshot. NEVER invent.
- You cannot execute anything. To take an action, call exactly one tool and
  the system will queue it as a PROPOSED action for a human to approve.
- If the snapshot does not contain enough information to answer, say so.
- Never quote or repeat advertiser/subscriber names not present in the
  snapshot.
- Tone: concise, professional, friendly. No emojis. No marketing language.
"""


@dataclass(frozen=True)
class AssistantTurnResult:
    assistant_text: str
    model_used: str
    proposed_action_ids: list[int]


def _format_tool_calls_summary(name: str, args: dict[str, Any]) -> str:
    if name == "propose_renewal_draft":
        return f"Draft renewal proposal for advertiser #{args.get('advertiser_id')}"
    if name == "propose_send_renewal_reminder":
        return f"Send renewal reminder to subscriber #{args.get('subscriber_id')}"
    if name == "propose_assign_complaint":
        return (
            f"Assign complaint #{args.get('complaint_id')} to user "
            f"#{args.get('assignee_user_id')}"
        )
    return f"Run {name}"


def _build_messages(
    snapshot: dict, history: list[Message], user_text: str
) -> list[dict[str, Any]]:
    system = (
        SYSTEM_PROMPT
        + "\n\nSNAPSHOT (read-only):\n"
        + json.dumps(snapshot, ensure_ascii=False, indent=2)
    )
    msgs: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in history:
        if m.role == MessageRole.USER:
            msgs.append({"role": "user", "content": m.content})
        elif m.role == MessageRole.ASSISTANT:
            msgs.append({"role": "assistant", "content": m.content})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def reply(
    db: Session,
    *,
    conversation: Conversation,
    user_text: str,
) -> AssistantTurnResult:
    """Run one assistant turn. Persists the new user message, the assistant
    reply, and any proposed actions. Commits before returning."""

    # 1. Persist the user message first so it's always recorded even if the
    #    model call fails later.
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=user_text,
    )
    db.add(user_msg)
    db.flush()

    # 2. Build prompt and call the model (with tools).
    snapshot = build_crm_snapshot(db)
    history = list(conversation.messages)[:-1]  # exclude the just-added user_msg
    messages = _build_messages(snapshot, history, user_text)

    try:
        result: ChatResult = chat_messages(
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=700,
            temperature=0.3,
        )
    except AIDisabledError:
        reply_text = (
            "The assistant is offline (no OPENROUTER_API_KEY configured). "
            "I can still record questions for review, but I can't answer or "
            "propose actions right now."
        )
        a_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply_text,
        )
        db.add(a_msg)
        db.commit()
        return AssistantTurnResult(
            assistant_text=reply_text,
            model_used="DISABLED",
            proposed_action_ids=[],
        )
    except AIClientError as e:
        log.warning("assistant chat failed: %s", e)
        reply_text = (
            "Sorry — the AI service errored on that one. The team has been "
            "notified; please try again."
        )
        a_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=reply_text,
        )
        db.add(a_msg)
        db.commit()
        return AssistantTurnResult(
            assistant_text=reply_text,
            model_used="ERROR",
            proposed_action_ids=[],
        )

    # 3. Persist the assistant message (and any tool calls, as JSON).
    assistant_text = (result.content or "").strip() or (
        "(no text reply — see proposed action below)"
    )
    a_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=assistant_text,
        tool_calls=result.tool_calls,
    )
    db.add(a_msg)
    db.flush()

    # 4. Convert tool calls into pending proposed actions. Do not execute.
    proposed_ids: list[int] = []
    for tc in result.tool_calls or []:
        try:
            fn = tc["function"]
            name = fn["name"]
            raw_args = fn.get("arguments") or "{}"
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            log.warning("malformed tool call from model, skipping: %s (%s)", tc, e)
            continue
        # Whitelist tool names — anything unknown is dropped, not stored.
        if name not in {t["function"]["name"] for t in TOOLS}:
            log.warning("model proposed unknown tool '%s', dropping", name)
            continue
        pa = ProposedAction(
            conversation_id=conversation.id,
            message_id=a_msg.id,
            tool_name=name,
            arguments=args,
            summary=_format_tool_calls_summary(name, args),
        )
        db.add(pa)
        db.flush()
        proposed_ids.append(pa.id)

    # 5. Stamp the model used on the conversation for visibility.
    conversation.model_used = result.model

    db.commit()
    db.refresh(a_msg)
    return AssistantTurnResult(
        assistant_text=assistant_text,
        model_used=result.model,
        proposed_action_ids=proposed_ids,
    )


# ---------------------------------------------------------------------------
# Tool dispatchers — called when a user APPROVES a proposed action.
# These are the only places assistant intent crosses into mutation.
# ---------------------------------------------------------------------------
def execute_approved_action(db: Session, action: ProposedAction) -> dict[str, Any]:
    """Approval handler. Runs the corresponding domain mutation, returns
    a JSON-serialisable result, marks the action EXECUTED. Caller commits.
    """
    from app.ai.drafter import draft_proposal  # local import to avoid cycle
    from app.engines.churn import score_churn
    from app.models.advertiser import Advertiser
    from app.models.complaint import Complaint
    from app.models.proposal import Proposal, ProposalSource, ProposalStatus
    from app.models.user import User
    from app.services.churn import days_to_active_contract_expiry

    name = action.tool_name
    args = action.arguments or {}

    if name == "propose_renewal_draft":
        adv = db.get(Advertiser, args.get("advertiser_id"))
        if adv is None:
            return {"error": "advertiser not found"}
        churn = score_churn(
            spend_trend=float(adv.spend_trend or 0),
            open_rate=float(adv.proposal_open_rate or 0),
            days_to_expiry=days_to_active_contract_expiry(adv),
        )
        drafted = draft_proposal(adv, churn.reasons)
        p = Proposal(
            advertiser_id=adv.id,
            subject=drafted.subject,
            body=drafted.body,
            source=ProposalSource.AI_DRAFT,
            status=ProposalStatus.DRAFT,
            needs_human=drafted.needs_human,
            needs_human_reason=drafted.needs_human_reason,
            model_used=drafted.model_used,
            created_by_id=action.decided_by_id,
        )
        db.add(p)
        db.flush()
        return {"proposal_id": p.id, "needs_human": drafted.needs_human}

    if name == "propose_assign_complaint":
        c = db.get(Complaint, args.get("complaint_id"))
        if c is None:
            return {"error": "complaint not found"}
        assignee = db.get(User, args.get("assignee_user_id"))
        if assignee is None:
            return {"error": "user not found"}
        c.assigned_to_id = assignee.id
        return {"complaint_id": c.id, "assigned_to_id": assignee.id}

    if name == "propose_send_renewal_reminder":
        # Stub: in Sprint 9 the notifications service will send the email.
        return {"queued": True, "subscriber_id": args.get("subscriber_id")}

    return {"error": f"unknown tool {name}"}
