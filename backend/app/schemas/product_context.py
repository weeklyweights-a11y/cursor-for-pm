from uuid import UUID

from pydantic import BaseModel, Field


class ProductContextCreateRequest(BaseModel):
    """Request body for POST product-context."""

    product_name: str = Field(..., min_length=1, max_length=255)
    product_description: str = Field(..., min_length=1)
    existing_features: list[str] = Field(default_factory=list)
    target_users: str | None = Field(None, max_length=500)
    known_limitations: list[str] | None = None
    additional_context: str | None = None


class ProductContextUpdateRequest(BaseModel):
    """Request body for PATCH product-context."""

    product_name: str | None = Field(None, min_length=1, max_length=255)
    product_description: str | None = Field(None, min_length=1)
    existing_features: list[str] | None = None
    target_users: str | None = Field(None, max_length=500)
    known_limitations: list[str] | None = None
    additional_context: str | None = None


class ProductContextResponse(BaseModel):
    """Response for GET product-context."""

    id: UUID
    org_id: UUID
    product_name: str
    product_description: str
    existing_features: list[str]
    target_users: str | None
    known_limitations: list[str] | None
    additional_context: str | None

    class Config:
        from_attributes = True
