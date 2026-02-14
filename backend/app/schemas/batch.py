from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BatchResponse(BaseModel):
    """Batch status and progress."""

    id: UUID
    org_id: UUID
    filename: str
    total_rows: int
    processed_rows: int
    successful_rows: int
    failed_rows: int
    status: str
    error_message: str | None
    column_mapping: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CSVUploadResponse(BaseModel):
    """Response after CSV upload: either completed batch (sync) or batch_id + status pending (async)."""

    batch: BatchResponse
    sync: bool  # True if processed synchronously
    message: str | None = None
