from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ThemeResponse(BaseModel):
    """Theme in list or detail; centroid excluded in list or as list of floats."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None = None
    mention_count: int = 0
    unique_customers: int = 0
    segment_breakdown: dict | None = None
    urgency_breakdown: dict | None = None
    sentiment_breakdown: dict | None = None
    top_quotes: list | None = None
    priority_score: float = 0.0
    score_breakdown: dict | None = None
    is_current: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ThemeListResponse(BaseModel):
    """Paginated list of themes."""

    data: list[ThemeResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class ThemeDetailResponse(BaseModel):
    """Theme with optional paginated feedback."""

    theme: ThemeResponse
    feedback_page: int | None = None
    feedback_page_size: int | None = None
    feedback_total: int | None = None
    feedback_total_pages: int | None = None
    feedback_items: list | None = None
