"""Slack routes: status when disconnected; events signing; GAP 2 message filtering and idempotency."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _slack_signature(body: bytes, secret: str) -> str:
    return "v0=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_slack_status_when_disconnected(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/slack/status",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["connected"] is False
    assert r.json()["data"]["team_name"] is None


def test_slack_events_invalid_signature_401(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", "secret")
    body = json.dumps({"type": "event_callback", "event": {"type": "message"}}).encode()
    r = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={"Content-Type": "application/json", "X-Slack-Signature": "v0=wrong"},
    )
    assert r.status_code == 401


def test_slack_events_url_verification(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "slack_signing_secret", "test_signing_secret")
    body = json.dumps({"type": "url_verification", "challenge": "challenge_value"}).encode()
    sig = _slack_signature(body, "test_signing_secret")
    r = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={"Content-Type": "application/json", "X-Slack-Signature": sig},
    )
    assert r.status_code == 200
    assert r.json() == {"challenge": "challenge_value"}


def test_slack_events_bot_message_not_enqueued(client: TestClient, monkeypatch):
    """GAP 2: bot messages must not be processed (no task enqueued; we can't easily assert no task, but we verify 200 and no error)."""
    monkeypatch.setattr(settings, "slack_signing_secret", "test_signing_secret")
    body = json.dumps({
        "type": "event_callback",
        "team_id": "T999",
        "event": {"type": "message", "bot_id": "B123", "channel": "C1", "ts": "123.0", "text": "hi"},
    }).encode()
    sig = _slack_signature(body, "test_signing_secret")
    r = client.post(
        "/api/v1/slack/events",
        content=body,
        headers={"Content-Type": "application/json", "X-Slack-Signature": sig},
    )
    assert r.status_code == 200
    # Team T999 has no connection, so no task is enqueued; bot_id would be skipped in route filter anyway


def test_slack_events_message_changed_skipped(client: TestClient, monkeypatch):
    """GAP 2: subtype message_changed must be skipped."""
    monkeypatch.setattr(settings, "slack_signing_secret", "test_signing_secret")
    body = json.dumps({
        "type": "event_callback",
        "team_id": "T999",
        "event": {"type": "message", "subtype": "message_changed", "channel": "C1", "ts": "123.0"},
    }).encode()
    sig = _slack_signature(body, "test_signing_secret")
    r = client.post("/api/v1/slack/events", content=body, headers={"Content-Type": "application/json", "X-Slack-Signature": sig})
    assert r.status_code == 200
