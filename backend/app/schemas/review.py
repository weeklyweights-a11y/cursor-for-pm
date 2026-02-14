from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewQueueItemResponse(BaseModel):
    """Single item in the PM review queue."""

    id: UUID
    org_id: UUID
    feedback_item_id: UUID
    source_domain: str
    source_company_name: str | None = None
    candidate_customer_id: UUID | None = None
    candidate_customer_name: str | None = None
    candidate_domain: str | None = None
    confidence: float | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualMatchRequest(BaseModel):
    """Request body for manual match on a review item."""

    customer_id: UUID = Field(...)
