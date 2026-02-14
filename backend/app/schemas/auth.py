from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Request body for signup."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Request body for login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User in API responses."""

    id: UUID
    email: str
    name: str
    org_id: UUID
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    """Organization in API responses."""

    id: UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Response for signup: user, organization, token."""

    user: UserResponse
    organization: OrganizationResponse
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Response for login: user, token."""

    user: UserResponse
    access_token: str
    token_type: str = "bearer"
