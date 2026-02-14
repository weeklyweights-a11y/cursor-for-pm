import io
import os
import tempfile
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.feedback import (
    EnrichmentStatsResponse,
    ExtractionStatsResponse,
    FeedbackItemResponse,
    ManualFeedbackRequest,
    ManualMatchFeedbackRequest,
    pagination_meta,
)
from app.schemas.batch import BatchResponse
from app.services import batch_service, extraction_service, enrichment_service, feedback_service
from app.services.csv_service import ContentColumnNotFoundError, detect_columns, parse_csv_file

router = APIRouter(prefix="/feedback", tags=["feedback"])
MAX_FILE_BYTES = (settings.max_csv_file_size_mb or 10) * 1024 * 1024


@router.post("/manual")
def manual_feedback(
    body: ManualFeedbackRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Submit a single feedback item manually."""
    source_id = f"manual:{uuid.uuid4()}"
    item = feedback_service.create_feedback_item(
        db,
        current_user.org_id,
        content=body.content,
        source_type="manual",
        source_id=source_id,
        author_name=body.author_name,
        author_email=body.author_email,
        organization_name=body.organization_name,
        metadata_={"source_description": body.source_description} if body.source_description else None,
    )
    from app.tasks.extraction_tasks import extract_feedback_signals
    extract_feedback_signals.delay(str(item.id), str(current_user.org_id))
    return {"data": FeedbackItemResponse.model_validate(item).model_dump(by_alias=True)}


@router.post("/upload-csv")
async def upload_csv(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """Upload CSV. Sync if small; otherwise enqueue task and return batch_id."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .csv file.")
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {settings.max_csv_file_size_mb} MB limit.",
        )

    df = pd.read_csv(io.BytesIO(content), header=0)
    total_rows = len(df)
    if total_rows == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV has no data rows.")
    headers = list(df.columns)
    try:
        column_mapping = detect_columns(headers)
    except ContentColumnNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if total_rows <= settings.max_sync_csv_rows:
        # Sync: create batch, insert rows via create_feedback_items_batch
        from app.tasks.extraction_tasks import extract_feedback_signals
        batch = batch_service.create_batch(
            db, current_user.org_id, file.filename or "upload.csv", total_rows, column_mapping
        )
        total_success = 0
        total_failed = 0
        start_row = 0
        all_created_ids = []
        for chunk in parse_csv_file(file_content=content, column_mapping=column_mapping, chunk_size=500):
            created_ids, skipped = feedback_service.create_feedback_items_batch(
                db,
                current_user.org_id,
                batch.id,
                chunk,
                source_id_prefix=str(batch.id),
                start_row=start_row,
            )
            total_success += len(created_ids)
            total_failed += len(chunk) - len(created_ids) - skipped
            all_created_ids.extend(created_ids)
            start_row += len(chunk)
        for fid in all_created_ids:
            extract_feedback_signals.delay(str(fid), str(current_user.org_id))
        batch.processed_rows = total_rows
        batch.successful_rows = total_success
        batch.failed_rows = total_failed
        batch.status = "completed"
        db.commit()
        db.refresh(batch)
        return {
            "data": {
                "batch": BatchResponse.model_validate(batch),
                "sync": True,
                "message": f"Imported {total_success} items.",
            }
        }
    else:
        # Async: save to temp, create batch pending, enqueue
        batch = batch_service.create_batch(
            db, current_user.org_id, file.filename or "upload.csv", total_rows, column_mapping
        )
        tmp_dir = settings.csv_temp_dir or tempfile.gettempdir()
        Path(tmp_dir).mkdir(parents=True, exist_ok=True)
        path = os.path.join(tmp_dir, f"{batch.id}.csv")
        with open(path, "wb") as f:
            f.write(content)
        from app.tasks.csv_tasks import process_csv_batch as task_process_csv_batch
        task_process_csv_batch.delay(str(batch.id), str(current_user.org_id), path, column_mapping)
        b = batch_service.get_batch(db, current_user.org_id, batch.id)
        return {
            "data": {
                "batch": BatchResponse.model_validate(b),
                "sync": False,
                "message": "Processing in background. Poll GET /batches/{id} for progress.",
            }
        }


@router.get("")
def list_feedback(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    source_type: str | None = None,
    match_status: str | None = None,
    segment: str | None = None,
    theme_id: uuid.UUID | None = None,
    outliers_only: bool = False,
    unclustered_only: bool = False,
) -> dict:
    """List feedback items; paginated, optional filters including theme."""
    items, total = feedback_service.get_feedback_items(
        db,
        current_user.org_id,
        page=page,
        page_size=page_size,
        source_type_filter=source_type,
        match_status_filter=match_status,
        segment_filter=segment,
        theme_id_filter=theme_id,
        outliers_only=outliers_only,
        unclustered_only=unclustered_only,
    )
    out = []
    for i in items:
        d = FeedbackItemResponse.model_validate(i).model_dump(by_alias=True)
        d["theme_name"] = i.theme.name if i.theme else None
        out.append(d)
    return {
        "data": out,
        "pagination": pagination_meta(page, page_size, total),
    }


@router.get("/extraction-stats")
def get_extraction_stats(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get extraction counts (total, pending, completed, failed) for org feedback."""
    stats = extraction_service.get_extraction_stats(db, current_user.org_id)
    return {"data": ExtractionStatsResponse.model_validate(stats).model_dump()}


@router.get("/enrichment-stats")
def get_enrichment_stats(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get enrichment counts (matched, pm_review, unmatched) for org feedback."""
    stats = feedback_service.get_enrichment_stats(db, current_user.org_id)
    return {"data": EnrichmentStatsResponse.model_validate(stats).model_dump()}


@router.post("/extract-pending")
def extract_pending(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Enqueue extraction for all feedback items with status pending or failed."""
    from app.tasks.extraction_tasks import extract_feedback_signals

    ids = feedback_service.get_pending_extraction_ids(db, current_user.org_id)
    for item_id in ids:
        extract_feedback_signals.delay(str(item_id), str(current_user.org_id))
    return {"data": {"enqueued": len(ids)}}


@router.post("/{item_id}/manual-match")
def manual_match_feedback(
    item_id: uuid.UUID,
    body: ManualMatchFeedbackRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Manually match a feedback item to a customer. Cascades to same-domain items."""
    item = enrichment_service.manual_match_feedback_item(
        db, current_user.org_id, item_id, body.customer_id
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback item not found or customer invalid.",
        )
    return {"data": FeedbackItemResponse.model_validate(item).model_dump(by_alias=True)}


@router.get("/{item_id}")
def get_feedback(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get a single feedback item by id."""
    item = feedback_service.get_feedback_item(db, current_user.org_id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback item not found.")
    d = FeedbackItemResponse.model_validate(item).model_dump(by_alias=True)
    d["theme_name"] = item.theme.name if item.theme else None
    return {"data": d}


@router.delete("/{item_id}")
def delete_feedback(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Remove a feedback item. Org-scoped."""
    if not feedback_service.delete_feedback_item(db, current_user.org_id, item_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback item not found.")
    return {"data": {"status": "deleted"}}
