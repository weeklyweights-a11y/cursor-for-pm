"""Chat orchestration and CRUD (Phase 6)."""

import time
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.services import chat_context_builder
from app.services import embedding_service
from app.services import llm_chat
from app.services import tool_service
from app.services import tool_definitions
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_TOOL_CALLS_PER_TURN = 3


def create_conversation(db: Session, org_id: UUID, user_id: UUID, title: str | None = None) -> Conversation:
    """Create a new conversation."""
    conv = Conversation(org_id=org_id, user_id=user_id, title=title, is_active=True)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversations(
    db: Session,
    org_id: UUID,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Conversation], int]:
    """List user's conversations, most recent first. Compute message_count and last_message_at per row."""
    q = db.query(Conversation).filter(
        Conversation.org_id == org_id,
        Conversation.user_id == user_id,
        Conversation.is_active == True,
    )
    total = q.count()
    q = q.order_by(Conversation.updated_at.desc())
    convs = q.offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for c in convs:
        msg_count = db.query(Message).filter(Message.conversation_id == c.id).count()
        last_ts = db.query(func.max(Message.created_at)).filter(Message.conversation_id == c.id).scalar()
        result.append((c, msg_count, last_ts))
    return result, total


def get_conversation_messages(
    db: Session,
    org_id: UUID,
    user_id: UUID,
    conversation_id: UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Message], int]:
    """Messages for conversation, oldest first. Verify ownership."""
    conv = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.org_id == org_id,
        Conversation.user_id == user_id,
    ).first()
    if not conv:
        return [], 0
    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    total = q.count()
    items = q.order_by(Message.created_at.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_conversation(db: Session, org_id: UUID, user_id: UUID, conversation_id: UUID) -> Conversation | None:
    """Get conversation if it belongs to org and user."""
    return db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.org_id == org_id,
        Conversation.user_id == user_id,
    ).first()


def delete_conversation(db: Session, org_id: UUID, user_id: UUID, conversation_id: UUID) -> bool:
    """Soft delete (is_active=false). Returns True if found and updated."""
    conv = get_conversation(db, org_id, user_id, conversation_id)
    if not conv:
        return False
    conv.is_active = False
    db.commit()
    return True


def clear_conversation(db: Session, org_id: UUID, user_id: UUID, conversation_id: UUID) -> bool:
    """Delete all messages in the conversation. Returns True if found."""
    conv = get_conversation(db, org_id, user_id, conversation_id)
    if not conv:
        return False
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.commit()
    return True


def send_message(
    db: Session,
    org_id: UUID,
    user_id: UUID,
    content: str,
    conversation_id: UUID | None = None,
    page_context: dict | None = None,
) -> dict:
    """
    Full pipeline: create or load conversation, load history, embed query, build RAG context,
    build prompt, call LLM with tools (max 3 tool rounds), store user + assistant messages,
    queue auto_title on first message. Returns { "message": MessageResponse, "conversation_id": UUID }.
    """
    if not content or not content.strip():
        return {"error": "Content is required."}
    conv = None
    if conversation_id:
        conv = get_conversation(db, org_id, user_id, conversation_id)
        if not conv:
            return {"error": "Conversation not found."}
    if not conv:
        conv = create_conversation(db, org_id, user_id, title=None)
    is_first = db.query(Message).filter(Message.conversation_id == conv.id).count() == 0
    history, _ = get_conversation_messages(db, org_id, user_id, conv.id, page=1, page_size=getattr(settings, "chat_max_history", 20))
    history_for_prompt = [{"role": m.role, "content": m.content} for m in history]
    query_embedding = embedding_service.generate_embedding(content)
    rag_context = chat_context_builder.build_rag_context(db, org_id, query_embedding or [], content, page_context)
    system_prompt = chat_context_builder.get_system_prompt_with_context(db, org_id)
    system_prompt, history_for_prompt, rag_context = chat_context_builder.manage_context_window(
        system_prompt, history_for_prompt, rag_context, content
    )
    tools = tool_definitions.get_tool_definitions()
    tools_prompt = tool_definitions.get_ollama_tool_prompt()
    system_with_tools = system_prompt + "\n\n" + tools_prompt
    messages = chat_context_builder.build_chat_prompt(system_prompt, history_for_prompt, rag_context, content)
    user_msg = Message(conversation_id=conv.id, org_id=org_id, role="user", content=content.strip())
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    start = time.perf_counter()
    response_text = ""
    context_used = {"feedback_items_searched": getattr(settings, "chat_max_rag_items", 20), "tools_called": []}
    tool_calls_this_turn = []
    for _ in range(MAX_TOOL_CALLS_PER_TURN):
        response_text, tool_calls = llm_chat.call_chat_llm(system_with_tools, messages, tools=tools)
        if not tool_calls:
            break
        tool_calls_this_turn.extend(tool_calls)
        for tc in tool_calls:
            name = tc.get("name") or tc.get("tool")
            params = tc.get("input") or tc.get("params") or {}
            result = tool_service.execute_tool(db, org_id, name, params, user_id=user_id)
            if "id" in tc:
                messages.append({"role": "assistant", "content": [{"type": "tool_use", "id": tc["id"], "name": name, "input": params}]})
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": tc["id"], "content": str(result)}]})
            else:
                messages.append({"role": "user", "content": f"Tool {name} result: {result}"})
    duration_ms = int((time.perf_counter() - start) * 1000)
    context_used["tools_called"] = [t.get("name") or t.get("tool") for t in tool_calls_this_turn]
    assistant_msg = Message(
        conversation_id=conv.id,
        org_id=org_id,
        role="assistant",
        content=response_text,
        context_used=context_used,
        tool_calls={"calls": tool_calls_this_turn} if tool_calls_this_turn else None,
        duration_ms=duration_ms,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)
    if is_first:
        from app.tasks.chat_tasks import auto_title_task
        auto_title_task.delay(str(conv.id), content[:500])
    return {
        "message": assistant_msg,
        "conversation_id": conv.id,
    }
