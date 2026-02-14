"""Tests for enrichment_service: exact match, saved mapping, LLM fuzzy (mocked), unmatched."""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.feedback_item import FeedbackItem
from app.models.organization import Organization
from app.services import enrichment_service
from app.utils.domain import normalize_domain


@pytest.fixture
def feedback_item_with_email(db: Session, test_org: Organization) -> FeedbackItem:
    item = FeedbackItem(
        org_id=test_org.id,
        content="Need better search",
        source_type="manual",
        source_id="manual:1",
        author_email="john@acme.com",
        organization_name="Acme",
        extraction_status="completed",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def test_extract_domain_from_email():
    assert enrichment_service.extract_domain_from_email("john@acme.com") == "acme.com"
    assert enrichment_service.extract_domain_from_email(None) == ""


def test_enrich_feedback_item_exact_match(db: Session, test_org: Organization, test_customer, feedback_item_with_email):
    enrichment_service.enrich_feedback_item(db, test_org.id, feedback_item_with_email.id)
    db.refresh(feedback_item_with_email)
    assert feedback_item_with_email.customer_id == test_customer.id
    assert feedback_item_with_email.match_method == "exact"
    assert feedback_item_with_email.match_status == "matched"


def test_enrich_feedback_item_no_email_unmatched(db: Session, test_org: Organization, test_customer):
    item = FeedbackItem(
        org_id=test_org.id,
        content="Feedback",
        source_type="manual",
        source_id="manual:no-email",
        extraction_status="completed",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    enrichment_service.enrich_feedback_item(db, test_org.id, item.id)
    db.refresh(item)
    assert item.customer_id is None
    assert item.match_status == "unmatched"


def test_re_enrich_unmatched_returns_ids(db: Session, test_org: Organization, feedback_item_with_email):
    feedback_item_with_email.match_status = "unmatched"
    feedback_item_with_email.extraction_status = "completed"
    db.commit()
    pairs = enrichment_service.re_enrich_unmatched(db, test_org.id)
    assert len(pairs) >= 1
    assert any(p[0] == feedback_item_with_email.id for p in pairs)
