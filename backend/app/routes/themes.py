from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.feedback import FeedbackItemResponse, pagination_meta
from app.schemas.theme import ThemeResponse
from app.services import theme_service

router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("")
def list_themes(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "priority_score",
) -> dict:
    """List themes for org; is_current=true, paginated and sorted."""
    themes, total = theme_service.get_themes(db, current_user.org_id, page=page, page_size=page_size, sort_by=sort_by)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": [ThemeResponse.model_validate(t).model_dump() for t in themes],
        "pagination": {"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
    }


@router.get("/outliers")
def list_outliers(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List outlier feedback items (is_outlier=true, clustered)."""
    items, total = theme_service.get_outliers(db, current_user.org_id, page=page, page_size=page_size)
    out = []
    for i in items:
        d = FeedbackItemResponse.model_validate(i).model_dump(by_alias=True)
        d["theme_name"] = None
        out.append(d)
    return {"data": out, "pagination": pagination_meta(page, page_size, total)}


@router.get("/{theme_id}")
def get_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single theme by id (org-scoped)."""
    theme = theme_service.get_theme(db, current_user.org_id, theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theme not found.")
    return {"data": ThemeResponse.model_validate(theme).model_dump()}


@router.get("/{theme_id}/feedback")
def get_theme_feedback(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Get paginated feedback items for a theme."""
    theme = theme_service.get_theme(db, current_user.org_id, theme_id)
    if not theme:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theme not found.")
    items, total = theme_service.get_theme_feedback(db, current_user.org_id, theme_id, page=page, page_size=page_size)
    out = []
    for i in items:
        d = FeedbackItemResponse.model_validate(i).model_dump(by_alias=True)
        d["theme_name"] = theme.name
        out.append(d)
    return {"data": out, "pagination": pagination_meta(page, page_size, total)}
