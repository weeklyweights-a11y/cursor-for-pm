from datetime import datetime

from pydantic import BaseModel


class ClusteringResultResponse(BaseModel):
    """Result of a clustering run."""

    clusters_found: int
    outliers: int
    items_processed: int
    duration_ms: int


class ClusteringStatusResponse(BaseModel):
    """Current clustering status for the org."""

    is_running: bool
    last_run_at: datetime | None = None
    last_run_result: dict | None = None  # clusters_found, outliers, duration_ms
    items_pending: int
