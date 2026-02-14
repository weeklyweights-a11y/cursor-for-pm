from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdateRequest
from app.services.organization_service import get_organization, update_organization

router = APIRouter(prefix="/organization", tags=["organization"])


@router.get("")
def get_organization_endpoint(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Return the current user's organization. Filtered by org_id from token."""
    org = get_organization(db, current_user.org_id)
    return {"data": OrganizationResponse.model_validate(org).model_dump()}


@router.patch("")
def update_organization_endpoint(
    body: OrganizationUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Update the current user's organization name."""
    org = update_organization(db, current_user.org_id, body.name)
    return {"data": OrganizationResponse.model_validate(org).model_dump()}
