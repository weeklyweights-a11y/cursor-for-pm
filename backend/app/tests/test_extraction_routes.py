"""Tests for extraction-related routes. Manual triggers task; GET feedback has extraction fields; extraction-stats."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.organization import Organization


def test_manual_feedback_enqueues_extraction_task(client: TestClient, auth_token: str, test_org: Organization):
    with patch("app.tasks.extraction_tasks.extract_feedback_signals") as mock_task:
        r = client.post(
            "/api/v1/feedback/manual",
            json={"content": "Manual feedback for extraction"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert r.status_code == 200
    mock_task.delay.assert_called_once()
    args = mock_task.delay.call_args[0]
    assert len(args) == 2  # feedback_item_id, org_id


def test_get_feedback_item_includes_extraction_fields(
    client: TestClient, auth_token: str, test_org: Organization, db: Session
):
    from app.services import feedback_service
    item = feedback_service.create_feedback_item(
        db, test_org.id, "Content", "manual", "manual:ext-1"
    )
    item.extraction_status = "completed"
    item.topic = "search"
    item.urgency = "high"
    item.sentiment = "negative"
    item.extraction_confidence = 0.85
    db.commit()
    r = client.get(
        f"/api/v1/feedback/{item.id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data.get("extraction_status") == "completed"
    assert data.get("topic") == "search"
    assert data.get("urgency") == "high"
    assert data.get("sentiment") == "negative"
    assert data.get("extraction_confidence") == 0.85


def test_get_extraction_stats_route(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/feedback/extraction-stats",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert "total" in data
    assert "pending" in data
    assert "completed" in data
    assert "failed" in data
    assert data["total"] >= 0


def test_extraction_stats_route_before_item_route(client: TestClient, auth_token: str):
    """GET /feedback/extraction-stats must not be matched by GET /feedback/{item_id} (GAP 5)."""
    r = client.get(
        "/api/v1/feedback/extraction-stats",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert "total" in r.json()["data"]
