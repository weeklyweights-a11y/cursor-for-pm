from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LoginResponse,
    OrganizationResponse,
    SignupRequest,
    UserResponse,
)
from app.services.auth_service import login, signup
from app.middleware.auth import get_current_user_dependency
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup_endpoint(
    body: SignupRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Create organization and user, return user, organization, and JWT."""
    user, org, token = signup(
        db,
        body.email,
        body.password,
        body.name,
        body.organization_name,
    )
    response = AuthResponse(
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org),
        access_token=token,
    )
    return {"data": response.model_dump()}


@router.post("/login")
def login_endpoint(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Validate credentials and return user and JWT."""
    user, token = login(db, body.email, body.password)
    response = LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
    )
    return {"data": response.model_dump()}


@router.get("/me")
def me_endpoint(
    current_user: User = Depends(get_current_user_dependency),
) -> dict:
    """Return the current authenticated user."""
    return {"data": UserResponse.model_validate(current_user).model_dump()}