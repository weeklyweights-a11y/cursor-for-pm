"""Tests for review-queue routes: auth, org isolation, status/body."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.match_review import MatchReviewQueue
from app.models.organization import Organization


@pytest.fixture
def pending_review(client: TestClient, auth_token: str, test_org: Organization, test_user, test_customer, db: Session):
    """Create a pending review item for route tests."""
    item = FeedbackItem(
        org_id=test_org.id,
        content="Review me",
        source_type="manual",
        source_id="manual:rev1",
        author_email="u@src.com",
        extraction_status="completed",
        match_status="pm_review",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    review = MatchReviewQueue(
        org_id=test_org.id,
        feedback_item_id=item.id,
        source_domain="src.com",
        candidate_customer_id=test_customer.id,
        candidate_customer_name=test_customer.company_name,
        candidate_domain=test_customer.domain,
        confidence=0.7,
        status="pending",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def test_get_review_queue_200(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/review-queue",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert "data" in r.json()
    assert "pagination" in r.json()


def test_get_review_count_200(client: TestClient, auth_token: str):
    r = client.get(
        "/api/v1/review-queue/count",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert "data" in r.json()
    assert "count" in r.json()["data"]


def test_skip_review_200(client: TestClient, auth_token: str, pending_review):
    r = client.post(
        f"/api/v1/review-queue/{pending_review.id}/skip",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "skipped"


def test_review_requires_auth(client: TestClient):
    r = client.get("/api/v1/review-queue")
    assert r.status_code == 401
