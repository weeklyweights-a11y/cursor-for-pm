"""Chat request/response schemas (Phase 6)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class PageContextSchema(BaseModel):
    """Optional page context for RAG (theme, feedback, or customer)."""

    type: Literal["theme", "feedback", "customer"]
    id: str


class SendMessageRequest(BaseModel):
    """Request body for POST /chat/send."""

    content: str
    conversation_id: UUID | None = None
    page_context: PageContextSchema | None = None


class MessageResponse(BaseModel):
    """Single message in a conversation."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    context_used: dict | None = None
    tool_calls: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Conversation list item with computed message_count and last_message_at."""

    id: UUID
    title: str | None
    is_active: bool
    message_count: int = 0
    last_message_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Paginated list of conversations."""

    data: list[ConversationResponse]
    pagination: dict


class ConversationMessagesResponse(BaseModel):
    """Paginated list of messages."""

    data: list[MessageResponse]
    pagination: dict


class ChatResponse(BaseModel):
    """Response for POST /chat/send."""

    message: MessageResponse
    conversation_id: UUID
