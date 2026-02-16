"""Spec request/response schemas (Phase 8)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GenerateSpecRequest(BaseModel):
    """Request body for POST /specs/generate."""

    brief_id: UUID
    scope: str = "full"  # mvp, full
    target_audience: str = "mixed"  # ai_agent, engineer, mixed
    custom_instructions: str | None = None


class SpecSectionResponse(BaseModel):
    """Single section in a spec."""

    key: str
    title: str
    content: str
    generated_at: str | None = None
    edited: bool = False
    edit_history: list[dict] = []


class SpecResponse(BaseModel):
    """Full spec with sections."""

    id: UUID
    brief_id: UUID
    theme_id: UUID
    version: int
    status: str
    title: str
    scope: str
    target_audience: str
    sections: list[SpecSectionResponse] = []
    config: dict | None = None
    metadata: dict | None = None
    is_current: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SpecListResponse(BaseModel):
    """List of specs."""

    data: list[SpecResponse]
    pagination: dict | None = None


class EditSpecSectionRequest(BaseModel):
    """Request body for PATCH section."""

    content: str


class RegenerateSpecSectionRequest(BaseModel):
    """Request body for POST section regenerate (optional empty body)."""

    pass


class SpecExportResponse(BaseModel):
    """Export result."""

    markdown_content: str
    filename: str
    format: str  # "standard" or "cursor"


class SpecStatusResponse(BaseModel):
    """Generation progress."""

    spec_id: str
    status: str
    sections_completed: int
    sections_total: int
    current_section: str | None = None
