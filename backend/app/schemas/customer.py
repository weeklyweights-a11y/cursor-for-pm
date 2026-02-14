from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerUploadResponse(BaseModel):
    """Response after customer CSV upload."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    items_queued: int = 0  # unmatched feedback items queued for re-enrichment


class CustomerResponse(BaseModel):
    """Customer in list responses."""

    id: UUID
    org_id: UUID
    domain: str
    company_name: str | None = None
    segment: str | None = None
    metadata: dict | None = None  # extra CSV columns (e.g. renewal_quarter, contract_value, notes)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TopCustomerResponse(BaseModel):
    """Customer with feedback count for top-customers list."""

    id: UUID
    domain: str
    company_name: str | None = None
    metadata: dict | None = None
    feedback_count: int = 0

    model_config = {"from_attributes": True}


class CustomerDetailResponse(CustomerResponse):
    """Customer with feedback stats."""

    feedback_count: int = 0
    feedback_by_source: dict = Field(default_factory=dict)  # e.g. {"csv": 5, "slack": 2}
    latest_feedback_date: datetime | None = None
