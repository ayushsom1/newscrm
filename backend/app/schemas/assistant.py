from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.assistant import MessageRole, ProposedActionStatus


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: MessageRole
    content: str
    tool_calls: list[Any] | None = None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    model_used: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ProposedActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    message_id: int
    tool_name: str
    arguments: dict[str, Any]
    summary: str
    status: ProposedActionStatus
    decided_by_id: int | None
    decided_at: datetime | None
    result: dict[str, Any] | None
    created_at: datetime


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: int
    assistant_text: str
    model_used: str
    proposed_actions: list[ProposedActionOut] = []
