"""Brief request/response schemas (Phase 7)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GenerateBriefRequest(BaseModel):
    """Request body for POST /briefs/generate."""

    theme_id: UUID


class BriefSectionResponse(BaseModel):
    """Single section in a brief."""

    key: str
    title: str
    content: str
    generated_at: str | None = None
    edited: bool = False
    edit_history: list[dict] = []


class SolutionEvaluationResponse(BaseModel):
    """Solution evaluation result."""

    pain_points_addressed: list[dict] = []
    coverage_score: float = 0.0
    segment_impact: dict = {}
    strengths: list[str] = []
    gaps: list[str] = []
    recommended_additions: list[str] = []
    predicted_impact_score: float = 0.0


class BriefResponse(BaseModel):
    """Full brief with sections and optional solution_evaluation."""

    id: UUID
    theme_id: UUID
    version: int
    status: str
    title: str
    sections: list[BriefSectionResponse] = []
    solution_evaluation: dict | None = None
    metadata: dict | None = None
    is_current: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BriefListResponse(BaseModel):
    """Paginated list of briefs."""

    data: list[BriefResponse]
    pagination: dict


class EditSectionRequest(BaseModel):
    """Request body for PATCH section."""

    content: str


class RegenerateSectionRequest(BaseModel):
    """Request body for POST section regenerate (optional empty body)."""

    pass


class EvaluateSolutionRequest(BaseModel):
    """Request body for POST evaluate-solution."""

    solution_description: str


class BriefExportResponse(BaseModel):
    """Export result."""

    markdown_content: str
    filename: str


class BriefStatusResponse(BaseModel):
    """Generation progress."""

    brief_id: str
    status: str
    sections_completed: int
    sections_total: int
    current_section: str | None = None
