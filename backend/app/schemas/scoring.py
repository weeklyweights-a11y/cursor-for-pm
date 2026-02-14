from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ScoreBreakdownFactor(BaseModel):
    """Per-factor score: raw, normalized, weighted."""

    raw: float | int | None = None
    normalized: float | None = None
    weighted: float | None = None


class ScoringConfigResponse(BaseModel):
    """Current scoring config for the org."""

    id: UUID
    org_id: UUID
    goals: list[str] | None = None
    target_segments: list[str] | None = None
    weight_volume: float = 0.25
    weight_reach: float = 0.20
    weight_urgency: float = 0.25
    weight_sentiment: float = 0.15
    weight_strategic_fit: float = 0.15
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScoringConfigUpdateRequest(BaseModel):
    """Update goals, segments, and weights; weights must sum to 1.0."""

    goals: list[str] | None = None
    target_segments: list[str] | None = None
    weight_volume: float | None = None
    weight_reach: float | None = None
    weight_urgency: float | None = None
    weight_sentiment: float | None = None
    weight_strategic_fit: float | None = None

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "ScoringConfigUpdateRequest":
        w = [
            self.weight_volume,
            self.weight_reach,
            self.weight_urgency,
            self.weight_sentiment,
            self.weight_strategic_fit,
        ]
        if all(x is None for x in w):
            return self
        if any(x is None for x in w):
            return self  # partial update; service layer validates after merge
        total = sum(w)  # type: ignore[arg-type]
        if abs(total - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")
        return self
