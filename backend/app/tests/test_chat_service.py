"""Tests for chat service (Phase 6)."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.user import User
from app.services import chat_service

_FAKE_EMBEDDING = [0.1] * 384


def test_create_conversation(db: Session, test_org: Organization, test_user: User):
    conv = chat_service.create_conversation(db, test_org.id, test_user.id, title="My chat")
    assert conv.id is not None
    assert conv.org_id == test_org.id
    assert conv.user_id == test_user.id
    assert conv.title == "My chat"
    assert conv.is_active is True


def test_get_conversations_returns_message_count_and_last_message_at(
    db: Session, test_org: Organization, test_user: User, sample_conversation: Conversation, sample_messages
):
    rows, total = chat_service.get_conversations(db, test_org.id, test_user.id, page=1, page_size=20)
    assert total >= 1
    conv, message_count, last_message_at = rows[0]
    assert conv.id == sample_conversation.id
    assert message_count == 3
    assert last_message_at is not None


def test_get_conversation_messages_ordered_oldest_first(
    db: Session, test_org: Organization, test_user: User, sample_conversation: Conversation, sample_messages
):
    items, total = chat_service.get_conversation_messages(
        db, test_org.id, test_user.id, sample_conversation.id, page=1, page_size=50
    )
    assert total == 3
    assert len(items) == 3
    assert items[0].role == "user" and items[0].content == "First user message"
    assert items[1].role == "assistant"
    assert items[2].role == "user" and items[2].content == "Second user message"


def test_get_conversation_messages_other_user_empty(
    db: Session, test_org: Organization, second_user: User, sample_conversation: Conversation
):
    """Conversation belongs to test_user; second_user is in same org but different user -> no access."""
    items, total = chat_service.get_conversation_messages(
        db, test_org.id, second_user.id, sample_conversation.id, page=1, page_size=50
    )
    assert total == 0
    assert len(items) == 0


def test_delete_conversation_soft_deletes(
    db: Session, test_org: Organization, test_user: User, sample_conversation: Conversation
):
    ok = chat_service.delete_conversation(db, test_org.id, test_user.id, sample_conversation.id)
    assert ok is True
    db.refresh(sample_conversation)
    assert sample_conversation.is_active is False


def test_clear_conversation_removes_messages(
    db: Session, test_org: Organization, test_user: User, sample_conversation: Conversation, sample_messages
):
    ok = chat_service.clear_conversation(db, test_org.id, test_user.id, sample_conversation.id)
    assert ok is True
    items, total = chat_service.get_conversation_messages(db, test_org.id, test_user.id, sample_conversation.id)
    assert total == 0
    assert len(items) == 0


def test_send_message_creates_new_conversation(db: Session, test_org: Organization, test_user: User):
    with patch("app.services.chat_service.embedding_service.generate_embedding", return_value=_FAKE_EMBEDDING):
        with patch("app.services.chat_service.llm_chat.call_chat_llm", return_value=("Hello from assistant", [])):
            result = chat_service.send_message(db, test_org.id, test_user.id, "What are top priorities?")
    assert "error" not in result
    assert result["conversation_id"] is not None
    assert result["message"].role == "assistant"
    assert result["message"].content == "Hello from assistant"
    assert result["message"].context_used is not None


def test_send_message_appends_to_existing(
    db: Session, test_org: Organization, test_user: User, sample_conversation: Conversation, sample_messages
):
    with patch("app.services.chat_service.embedding_service.generate_embedding", return_value=_FAKE_EMBEDDING):
        with patch("app.services.chat_service.llm_chat.call_chat_llm", return_value=("Follow-up reply", [])):
            result = chat_service.send_message(
                db, test_org.id, test_user.id, "Another question",
                conversation_id=sample_conversation.id,
            )
    assert "error" not in result
    assert result["conversation_id"] == sample_conversation.id
    assert result["message"].content == "Follow-up reply"
    items, total = chat_service.get_conversation_messages(db, test_org.id, test_user.id, sample_conversation.id)
    assert total == 5


def test_send_message_empty_content_returns_error(db: Session, test_org: Organization, test_user: User):
    result = chat_service.send_message(db, test_org.id, test_user.id, "   ")
    assert "error" in result
    assert "content" in result["error"].lower()


def test_send_message_conversation_not_found_returns_error(db: Session, test_org: Organization, test_user: User):
    import uuid
    fake_id = uuid.uuid4()
    result = chat_service.send_message(db, test_org.id, test_user.id, "Hi", conversation_id=fake_id)
    assert "error" in result
    assert "not found" in result["error"].lower()
