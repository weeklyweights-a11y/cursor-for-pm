"""Chat API (Phase 6)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.chat import (
    ChatResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/send")
def send_message(
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Send a message. Creates new conversation if no conversation_id. Returns assistant message + conversation_id."""
    page_ctx = body.page_context.model_dump() if body.page_context else None
    result = chat_service.send_message(
        db,
        current_user.org_id,
        current_user.id,
        body.content,
        conversation_id=body.conversation_id,
        page_context=page_ctx,
    )
    if "error" in result:
        if "not found" in result["error"].lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    msg = result["message"]
    return {
        "data": {
            "message": MessageResponse.model_validate(msg).model_dump(),
            "conversation_id": str(result["conversation_id"]),
        }
    }


@router.get("/conversations")
def list_conversations(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List current user's conversations, most recent first. Paginated."""
    rows, total = chat_service.get_conversations(db, current_user.org_id, current_user.id, page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    data = []
    for conv, message_count, last_message_at in rows:
        data.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                is_active=conv.is_active,
                message_count=message_count,
                last_message_at=last_message_at,
                created_at=conv.created_at,
            )
        )
    return {
        "data": [c.model_dump() for c in data],
        "pagination": {"page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages},
    }


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Get messages for a conversation. Oldest first. Ownership verified."""
    items, total = chat_service.get_conversation_messages(
        db, current_user.org_id, current_user.id, conversation_id, page=page, page_size=page_size
    )
    if not items and total == 0:
        conv = chat_service.get_conversation(db, current_user.org_id, current_user.id, conversation_id)
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": [MessageResponse.model_validate(m).model_dump() for m in items],
        "pagination": {"page": page, "page_size": page_size, "total_items": total, "total_pages": total_pages},
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Soft delete conversation (is_active=false)."""
    ok = chat_service.delete_conversation(db, current_user.org_id, current_user.id, conversation_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"data": {"deleted": True}}


@router.post("/conversations/{conversation_id}/clear")
def clear_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Clear all messages in the conversation. Conversation remains."""
    ok = chat_service.clear_conversation(db, current_user.org_id, current_user.id, conversation_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return {"data": {"cleared": True}}
