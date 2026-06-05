from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai.assistant import execute_approved_action, reply
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import ASSISTANT_LIMIT, _user_key, limiter
from app.models.assistant import (
    Conversation,
    ProposedAction,
    ProposedActionStatus,
)
from app.models.user import User
from app.schemas.assistant import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    ProposedActionOut,
)
from app.services.audit import write_audit

router = APIRouter(tags=["assistant"])


def _get_user_conversation(
    db: Session, conversation_id: int, user: User
) -> Conversation:
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="conversation not found")
    return convo


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Conversation]:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    ).all()
    return list(rows)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    return _get_user_conversation(db, conversation_id, user)


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    convo = _get_user_conversation(db, conversation_id, user)
    db.delete(convo)
    db.commit()


@router.post("/ai/chat", response_model=ChatResponse)
@limiter.limit(ASSISTANT_LIMIT, key_func=_user_key)
def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    if payload.conversation_id:
        convo = _get_user_conversation(db, payload.conversation_id, user)
    else:
        convo = Conversation(
            user_id=user.id,
            title=payload.message[:80],
        )
        db.add(convo)
        db.flush()

    result = reply(db, conversation=convo, user_text=payload.message)
    # reload proposed actions created in this turn
    pa_rows = db.scalars(
        select(ProposedAction).where(
            ProposedAction.id.in_(result.proposed_action_ids)
        )
    ).all() if result.proposed_action_ids else []

    return ChatResponse(
        conversation_id=convo.id,
        assistant_text=result.assistant_text,
        model_used=result.model_used,
        proposed_actions=[ProposedActionOut.model_validate(p) for p in pa_rows],
    )


@router.get(
    "/conversations/{conversation_id}/proposed-actions",
    response_model=list[ProposedActionOut],
)
def list_proposed_actions(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProposedAction]:
    _get_user_conversation(db, conversation_id, user)
    rows = db.scalars(
        select(ProposedAction)
        .where(ProposedAction.conversation_id == conversation_id)
        .order_by(ProposedAction.id.desc())
    ).all()
    return list(rows)


@router.post(
    "/proposed-actions/{action_id}/approve", response_model=ProposedActionOut
)
def approve_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProposedAction:
    action = db.get(ProposedAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="action not found")
    convo = _get_user_conversation(db, action.conversation_id, user)
    if action.status != ProposedActionStatus.PENDING:
        raise HTTPException(
            status_code=409, detail=f"action is {action.status.value}"
        )
    action.decided_by_id = user.id
    result = execute_approved_action(db, action)
    action.status = (
        ProposedActionStatus.EXECUTED
        if "error" not in result
        else ProposedActionStatus.APPROVED  # decided but not executable
    )
    action.decided_at = datetime.now(timezone.utc)
    action.result = result
    write_audit(
        db,
        actor=user,
        action="approve_proposed_action",
        entity="proposed_action",
        entity_id=action.id,
        payload={
            "tool": action.tool_name,
            "arguments": action.arguments,
            "result": result,
            "conversation_id": convo.id,
        },
    )
    db.commit()
    db.refresh(action)
    return action


@router.post(
    "/proposed-actions/{action_id}/reject", response_model=ProposedActionOut
)
def reject_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProposedAction:
    action = db.get(ProposedAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="action not found")
    convo = _get_user_conversation(db, action.conversation_id, user)
    if action.status != ProposedActionStatus.PENDING:
        raise HTTPException(
            status_code=409, detail=f"action is {action.status.value}"
        )
    action.status = ProposedActionStatus.REJECTED
    action.decided_by_id = user.id
    action.decided_at = datetime.now(timezone.utc)
    write_audit(
        db,
        actor=user,
        action="reject_proposed_action",
        entity="proposed_action",
        entity_id=action.id,
        payload={
            "tool": action.tool_name,
            "conversation_id": convo.id,
        },
    )
    db.commit()
    db.refresh(action)
    return action
