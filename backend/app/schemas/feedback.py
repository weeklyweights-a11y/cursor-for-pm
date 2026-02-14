from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ManualFeedbackRequest(BaseModel):
    """Request body for manual feedback submission."""

    content: str = Field(..., min_length=1)
    author_name: str | None = Field(None, max_length=255)
    author_email: str | None = Field(None, max_length=255)
    organization_name: str | None = Field(None, max_length=255)
    source_description: str | None = Field(None, max_length=500)


class ManualMatchFeedbackRequest(BaseModel):
    """Request body for manual match (feedback item to customer)."""

    customer_id: UUID = Field(...)


class FeedbackItemResponse(BaseModel):
    """Single feedback item in API responses."""

    id: UUID
    org_id: UUID
    content: str
    source_type: str
    source_id: str
    timestamp: datetime | None
    author_email: str | None
    author_name: str | None
    organization_name: str | None
    metadata_: dict | None = Field(None, serialization_alias="metadata")
    batch_id: UUID | None
    created_at: datetime
    updated_at: datetime
    # Extraction (Phase 3)
    pain_point: str | None = None
    topic: str | None = None
    related_feature: str | None = None
    is_existing_feature: bool | None = None
    feature_gap: str | None = None
    urgency: str | None = None
    sentiment: str | None = None
    verbatim_quote: str | None = None
    extraction_confidence: float | None = None
    extraction_status: str | None = None
    raw_llm_response: str | None = None
    extracted_at: datetime | None = None
    # Enrichment (Phase 4)
    customer_id: UUID | None = None
    customer_domain: str | None = None
    customer_name: str | None = None
    segment: str | None = None
    match_method: str | None = None
    match_confidence: float | None = None
    match_status: str | None = None
    enriched_at: datetime | None = None
    # Phase 5
    theme_id: UUID | None = None
    theme_name: str | None = None
    is_outlier: bool | None = None
    clustered_at: datetime | None = None

    model_config = {"from_attributes": True}


class EnrichmentStatsResponse(BaseModel):
    """Enrichment counts by match status."""

    total: int
    matched: int
    pm_review: int
    unmatched: int


class ExtractionStatsResponse(BaseModel):
    """Extraction counts for org feedback items."""

    total: int
    pending: int
    completed: int
    failed: int


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int
    page_size: int
    total: int
    total_pages: int


def pagination_meta(page: int, page_size: int, total: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
