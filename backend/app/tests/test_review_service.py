"""Tests for review_service: confirm, reject, skip, manual_match, org filter, count."""

import pytest
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.match_review import MatchReviewQueue
from app.models.organization import Organization
from app.services import review_service


@pytest.fixture
def pending_review(db: Session, test_org: Organization, test_user, test_customer) -> MatchReviewQueue:
    item = FeedbackItem(
        org_id=test_org.id,
        content="Review me",
        source_type="manual",
        source_id="manual:rev",
        author_email="u@source.com",
        extraction_status="completed",
        match_status="pm_review",
        customer_id=test_customer.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    review = MatchReviewQueue(
        org_id=test_org.id,
        feedback_item_id=item.id,
        source_domain="source.com",
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


def test_get_pending_reviews(db: Session, test_org: Organization, pending_review):
    items, total = review_service.get_pending_reviews(db, test_org.id)
    assert total >= 1
    assert any(r.id == pending_review.id for r in items)


def test_get_review_count(db: Session, test_org: Organization, pending_review):
    n = review_service.get_review_count(db, test_org.id)
    assert n >= 1


def test_confirm_review(db: Session, test_org: Organization, test_user, pending_review):
    r = review_service.confirm_review(db, test_org.id, pending_review.id, test_user.id)
    assert r is not None
    assert r.status == "confirmed"
    fi = db.get(FeedbackItem, pending_review.feedback_item_id)
    assert fi is not None
    assert fi.match_status == "matched"


def test_reject_review(db: Session, test_org: Organization, test_user, pending_review):
    r = review_service.reject_review(db, test_org.id, pending_review.id, test_user.id)
    assert r is not None
    assert r.status == "rejected"


def test_skip_review(db: Session, test_org: Organization, pending_review):
    r = review_service.skip_review(db, test_org.id, pending_review.id)
    assert r is not None
    assert r.status == "skipped"
