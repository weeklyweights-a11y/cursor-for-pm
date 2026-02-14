from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.product_context import (
    ProductContextCreateRequest,
    ProductContextResponse,
    ProductContextUpdateRequest,
)
from app.services import product_context_service

router = APIRouter(prefix="/product-context", tags=["product-context"])


@router.get("", response_model=dict)
def get_product_context(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get current org's product context. 404 if not set."""
    ctx = product_context_service.get_product_context(db, current_user.org_id)
    return {"data": ProductContextResponse.model_validate(ctx).model_dump()}


@router.post("", response_model=dict)
def create_product_context(
    body: ProductContextCreateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Create product context for org. 400 if already exists."""
    ctx = product_context_service.create_product_context(db, current_user.org_id, body)
    return {"data": ProductContextResponse.model_validate(ctx).model_dump()}


@router.patch("", response_model=dict)
def update_product_context(
    body: ProductContextUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Update product context for org. 404 if not set."""
    ctx = product_context_service.update_product_context(db, current_user.org_id, body)
    return {"data": ProductContextResponse.model_validate(ctx).model_dump()}
