"""
Process CSV batch in background. GAP 4: source_id = f"{batch_id}:{row_number}".
GAP 5: check_duplicate before insert; idempotent.
"""

import logging
import time
from pathlib import Path
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services import batch_service, feedback_service
from app.services.csv_service import parse_csv_file

logger = logging.getLogger(__name__)
CHUNK_SIZE = 500


@celery_app.task(bind=True, name="app.tasks.csv_tasks.process_csv_batch")
def process_csv_batch(
    self,
    batch_id: str,
    org_id: str,
    file_path: str,
    column_mapping: dict,
) -> dict:
    """
    Process CSV file in chunks. Updates batch progress; completes or fails.
    Each row: source_id = batch_id:row_number; skip if duplicate (GAP 5).
    """
    batch_uuid = UUID(batch_id)
    org_uuid = UUID(org_id)
    path = Path(file_path)
    if not path.exists():
        db = SessionLocal()
        try:
            batch_service.fail_batch(db, batch_uuid, "CSV file not found.")
        finally:
            db.close()
        return {"status": "failed", "error": "File not found"}

    db = SessionLocal()
    try:
        batch_service.update_batch_progress(db, batch_uuid, 0, 0, 0)
    except Exception:
        pass
    finally:
        db.close()

    total_success = 0
    total_failed = 0
    total_processed = 0
    start = time.perf_counter()

    try:
        for chunk_idx, chunk in enumerate(
            parse_csv_file(file_path=file_path, column_mapping=column_mapping, chunk_size=CHUNK_SIZE)
        ):
            db = SessionLocal()
            try:
                start_row = chunk_idx * CHUNK_SIZE
                # GAP 4: source_id = batch_id:row_number
                created_ids, skipped = feedback_service.create_feedback_items_batch(
                    db,
                    org_uuid,
                    batch_uuid,
                    chunk,
                    source_id_prefix=str(batch_uuid),
                    start_row=start_row,
                )
                total_success += len(created_ids)
                # Rows not inserted: skipped (duplicate) or no content (count as failed)
                total_failed += len(chunk) - len(created_ids) - skipped
                total_processed += len(chunk)
                batch_service.update_batch_progress(
                    db,
                    batch_uuid,
                    total_processed,
                    total_success,
                    total_failed,
                )
                from app.tasks.extraction_tasks import extract_feedback_signals
                for fid in created_ids:
                    extract_feedback_signals.delay(str(fid), org_id)
            finally:
                db.close()
            logger.info(
                "csv_batch chunk batch_id=%s chunk=%s rows=%s inserted=%s skipped_dup=%s",
                batch_id,
                chunk_idx,
                len(chunk),
                len(created_ids),
                skipped,
            )

        db = SessionLocal()
        try:
            batch_service.complete_batch(db, batch_uuid)
        finally:
            db.close()
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "csv_batch completed batch_id=%s total_processed=%s successful=%s failed=%s duration_ms=%.0f",
            batch_id,
            total_processed,
            total_success,
            total_failed,
            elapsed_ms,
        )
        return {"status": "completed", "successful_rows": total_success, "failed_rows": total_failed}
    except Exception as e:
        logger.exception("csv_batch failed batch_id=%s", batch_id)
        db = SessionLocal()
        try:
            batch_service.fail_batch(db, batch_uuid, str(e))
        finally:
            db.close()
        return {"status": "failed", "error": str(e)}
