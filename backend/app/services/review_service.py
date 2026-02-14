"""
PM review queue: confirm, reject, skip, manual match. All org-scoped.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.customer import Customer
from app.models.domain_mapping import DomainMapping
from app.models.feedback_item import FeedbackItem
from app.models.match_review import MatchReviewQueue
from app.services.enrichment_service import (
    apply_match,
    extract_domain_from_email,
    save_mapping,
)
from app.utils.domain import normalize_domain


def get_pending_reviews(
    db: Session, org_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[MatchReviewQueue], int]:
    """List pending review items for org, paginated."""
    q = (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .order_by(MatchReviewQueue.created_at.desc())
    )
    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total


def get_review_count(db: Session, org_id: UUID) -> int:
    """Count of pending reviews for badge."""
    return (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .count()
    )


def _apply_match_to_same_domain_feedback(
    db: Session, org_id: UUID, source_domain: str, customer: Customer
) -> None:
    """Apply customer match to all feedback items with this source_domain (unmatched or pm_review)."""
    items = (
        db.query(FeedbackItem)
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.match_status.in_(("unmatched", "pm_review")),
        )
        .all()
    )
    for item in items:
        dom = (
            extract_domain_from_email(item.author_email)
            or normalize_domain(item.organization_name or "")
        )
        if dom == source_domain:
            apply_match(db, item, customer, "manual", 1.0, "matched")


def confirm_review(db: Session, org_id: UUID, review_id: UUID, user_id: UUID) -> MatchReviewQueue | None:
    """
    PM confirms the suggested match. Update mapping, feedback item, and all same-domain items.
    """
    review = (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.id == review_id,
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .first()
    )
    if not review or not review.candidate_customer_id:
        return None
    customer = db.get(Customer, review.candidate_customer_id)
    if not customer or customer.org_id != org_id:
        return None
    source_domain = review.source_domain
    save_mapping(
        db, org_id, source_domain, review.source_company_name,
        customer.id, review.confidence or 1.0, "manual", True,
    )
    feedback_item = db.get(FeedbackItem, review.feedback_item_id)
    if feedback_item:
        apply_match(db, feedback_item, customer, "manual", 1.0, "matched")
    _apply_match_to_same_domain_feedback(db, org_id, source_domain, customer)
    review.status = "confirmed"
    review.resolved_by = user_id
    review.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def reject_review(db: Session, org_id: UUID, review_id: UUID, user_id: UUID) -> MatchReviewQueue | None:
    """PM rejects: save negative mapping, mark review rejected, keep feedback unmatched."""
    review = (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.id == review_id,
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .first()
    )
    if not review:
        return None
    save_mapping(
        db, org_id, review.source_domain, review.source_company_name,
        None, 0.0, "manual", True,
    )
    feedback_item = db.get(FeedbackItem, review.feedback_item_id)
    if feedback_item:
        apply_match(db, feedback_item, None, "unmatched", 0.0, "unmatched")
    review.status = "rejected"
    review.resolved_by = user_id
    review.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return review


def skip_review(db: Session, org_id: UUID, review_id: UUID) -> MatchReviewQueue | None:
    """PM skips: only update review item status."""
    review = (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.id == review_id,
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .first()
    )
    if not review:
        return None
    review.status = "skipped"
    db.commit()
    db.refresh(review)
    return review


def manual_match_review(
    db: Session, org_id: UUID, review_id: UUID, customer_id: UUID, user_id: UUID
) -> MatchReviewQueue | None:
    """PM picks a different customer. Same as confirm but with chosen customer."""
    review = (
        db.query(MatchReviewQueue)
        .filter(
            MatchReviewQueue.id == review_id,
            MatchReviewQueue.org_id == org_id,
            MatchReviewQueue.status == "pending",
        )
        .first()
    )
    if not review:
        return None
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.org_id == org_id,
        Customer.is_active == True,
    ).first()
    if not customer:
        raise NotFoundError("Customer not found.")
    source_domain = review.source_domain
    save_mapping(
        db, org_id, source_domain, review.source_company_name,
        customer.id, 1.0, "manual", True,
    )
    feedback_item = db.get(FeedbackItem, review.feedback_item_id)
    if feedback_item:
        apply_match(db, feedback_item, customer, "manual", 1.0, "matched")
    _apply_match_to_same_domain_feedback(db, org_id, source_domain, customer)
    review.status = "confirmed"
    review.resolved_by = user_id
    review.resolved_at = datetime.now(timezone.utc)
    review.candidate_customer_id = customer.id
    review.candidate_customer_name = customer.company_name
    review.candidate_domain = customer.domain
    db.commit()
    db.refresh(review)
    return review
