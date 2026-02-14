from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.feedback import pagination_meta
from app.schemas.review import ManualMatchRequest, ReviewQueueItemResponse
from app.services import review_service

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


@router.get("")
def list_pending_reviews(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List pending review items for the org."""
    items, total = review_service.get_pending_reviews(
        db, current_user.org_id, page=page, page_size=page_size
    )
    return {
        "data": [ReviewQueueItemResponse.model_validate(r).model_dump() for r in items],
        "pagination": pagination_meta(page, page_size, total),
    }


@router.get("/count")
def get_review_count(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Count of pending reviews (for badge)."""
    count = review_service.get_review_count(db, current_user.org_id)
    return {"data": {"count": count}}


@router.post("/{review_id}/confirm")
def confirm_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Confirm the suggested match."""
    review = review_service.confirm_review(db, current_user.org_id, review_id, current_user.id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found.")
    return {"data": ReviewQueueItemResponse.model_validate(review).model_dump()}


@router.post("/{review_id}/reject")
def reject_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Reject the suggested match."""
    review = review_service.reject_review(db, current_user.org_id, review_id, current_user.id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found.")
    return {"data": ReviewQueueItemResponse.model_validate(review).model_dump()}


@router.post("/{review_id}/skip")
def skip_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Skip review for now."""
    review = review_service.skip_review(db, current_user.org_id, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found.")
    return {"data": ReviewQueueItemResponse.model_validate(review).model_dump()}


@router.post("/{review_id}/manual-match")
def manual_match_review(
    review_id: UUID,
    body: ManualMatchRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Override with PM's chosen customer."""
    review = review_service.manual_match_review(
        db, current_user.org_id, review_id, body.customer_id, current_user.id
    )
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found.")
    return {"data": ReviewQueueItemResponse.model_validate(review).model_dump()}
