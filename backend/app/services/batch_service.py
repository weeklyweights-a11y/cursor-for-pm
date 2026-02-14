from uuid import UUID

from sqlalchemy.orm import Session

from app.models.batch import Batch


def create_batch(
    db: Session,
    org_id: UUID,
    filename: str,
    total_rows: int,
    column_mapping: dict | None = None,
) -> Batch:
    """Create a new batch record (e.g. for async CSV processing)."""
    batch = Batch(
        org_id=org_id,
        filename=filename,
        total_rows=total_rows,
        processed_rows=0,
        successful_rows=0,
        failed_rows=0,
        status="pending",
        column_mapping=column_mapping,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def update_batch_progress(
    db: Session,
    batch_id: UUID,
    processed_rows: int,
    successful_rows: int,
    failed_rows: int,
) -> Batch | None:
    """Update batch progress (e.g. after processing a chunk)."""
    batch = db.get(Batch, batch_id)
    if not batch:
        return None
    batch.processed_rows = processed_rows
    batch.successful_rows = successful_rows
    batch.failed_rows = failed_rows
    batch.status = "processing"
    db.commit()
    db.refresh(batch)
    return batch


def complete_batch(db: Session, batch_id: UUID) -> Batch | None:
    """Set batch status to completed."""
    batch = db.get(Batch, batch_id)
    if not batch:
        return None
    batch.status = "completed"
    db.commit()
    db.refresh(batch)
    return batch


def fail_batch(db: Session, batch_id: UUID, error_message: str) -> Batch | None:
    """Set batch status to failed with message."""
    batch = db.get(Batch, batch_id)
    if not batch:
        return None
    batch.status = "failed"
    batch.error_message = error_message
    db.commit()
    db.refresh(batch)
    return batch


def get_batch(db: Session, org_id: UUID, batch_id: UUID) -> Batch | None:
    """Get a batch by id; must belong to org_id."""
    return db.query(Batch).filter(Batch.id == batch_id, Batch.org_id == org_id).first()


def get_batches(
    db: Session,
    org_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Batch], int]:
    """List batches for org with pagination. Returns (items, total_count)."""
    q = db.query(Batch).filter(Batch.org_id == org_id).order_by(Batch.created_at.desc())
    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total
