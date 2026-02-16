"""Tests for chat API routes (Phase 6)."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_post_send_new_conversation_returns_conversation_id(client: TestClient, auth_token: str):
    _fake_emb = [0.1] * 384
    with patch("app.services.chat_service.embedding_service.generate_embedding", return_value=_fake_emb):
        with patch("app.services.chat_service.llm_chat.call_chat_llm", return_value=("Test reply", [])):
            r = client.post(
                "/api/v1/chat/send",
                json={"content": "What are my top priorities?"},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "conversation_id" in data
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "Test reply"


def test_post_send_with_existing_conversation_appends(
    client: TestClient, auth_token: str, sample_conversation
):
    _fake_emb = [0.1] * 384
    with patch("app.services.chat_service.embedding_service.generate_embedding", return_value=_fake_emb):
        with patch("app.services.chat_service.llm_chat.call_chat_llm", return_value=("Second reply", [])):
            r = client.post(
                "/api/v1/chat/send",
                json={"content": "Follow up?", "conversation_id": str(sample_conversation.id)},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
    assert r.status_code == 200
    assert r.json()["data"]["conversation_id"] == str(sample_conversation.id)


def test_get_conversations_user_only(client: TestClient, auth_token: str, sample_conversation):
    r = client.get("/api/v1/chat/conversations", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data, list)
    ids = [c["id"] for c in data]
    assert str(sample_conversation.id) in ids


def test_get_conversations_other_user_different_list(
    client: TestClient, auth_token: str, second_auth_token: str, sample_conversation
):
    """test_user has sample_conversation; second_user (other org) should not see it."""
    r_other = client.get("/api/v1/chat/conversations", headers={"Authorization": f"Bearer {second_auth_token}"})
    assert r_other.status_code == 200
    data_other = r_other.json()["data"]
    ids_other = [c["id"] for c in data_other]
    assert str(sample_conversation.id) not in ids_other


def test_get_messages_ordered(client: TestClient, auth_token: str, sample_conversation, sample_messages):
    r = client.get(
        f"/api/v1/chat/conversations/{sample_conversation.id}/messages",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) == 3
    assert items[0]["role"] == "user"
    assert items[1]["role"] == "assistant"


def test_delete_conversation_soft_deletes(client: TestClient, auth_token: str, sample_conversation):
    r = client.delete(
        f"/api/v1/chat/conversations/{sample_conversation.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True


def test_delete_conversation_other_org_404(client: TestClient, second_auth_token: str, sample_conversation):
    """second_user is in second_org; sample_conversation is test_org -> 404."""
    r = client.delete(
        f"/api/v1/chat/conversations/{sample_conversation.id}",
        headers={"Authorization": f"Bearer {second_auth_token}"},
    )
    assert r.status_code == 404


def test_clear_conversation_success(client: TestClient, auth_token: str, sample_conversation, sample_messages):
    r = client.post(
        f"/api/v1/chat/conversations/{sample_conversation.id}/clear",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["cleared"] is True


def test_chat_requires_auth(client: TestClient):
    r = client.post("/api/v1/chat/send", json={"content": "Hi"})
    assert r.status_code == 401
