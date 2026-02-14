import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.batch import BatchResponse
from app.schemas.feedback import pagination_meta
from app.services import batch_service

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("")
def list_batches(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List CSV batches for the current org."""
    items, total = batch_service.get_batches(db, current_user.org_id, page=page, page_size=page_size)
    return {
        "data": [BatchResponse.model_validate(b) for b in items],
        "pagination": pagination_meta(page, page_size, total),
    }


@router.get("/{batch_id}")
def get_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get batch status and progress."""
    try:
        bid = uuid.UUID(batch_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    batch = batch_service.get_batch(db, current_user.org_id, bid)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return {"data": BatchResponse.model_validate(batch)}
