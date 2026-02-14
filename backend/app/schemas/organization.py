from pydantic import BaseModel, Field

from app.schemas.auth import OrganizationResponse


class OrganizationUpdateRequest(BaseModel):
    """Request body for PATCH organization."""

    name: str | None = Field(None, min_length=1, max_length=255)
