from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.feedback_item import FeedbackItem


def _parse_timestamp(value: str | datetime | None) -> datetime | None:
    """Parse timestamp string to datetime if needed."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def check_duplicate(db: Session, org_id: UUID, source_id: str) -> bool:
    """Return True if a feedback item with (org_id, source_id) already exists."""
    return db.query(FeedbackItem).filter(
        FeedbackItem.org_id == org_id,
        FeedbackItem.source_id == source_id,
    ).first() is not None


def create_feedback_item(
    db: Session,
    org_id: UUID,
    content: str,
    source_type: str,
    source_id: str,
    *,
    timestamp: datetime | str | None = None,
    author_email: str | None = None,
    author_name: str | None = None,
    organization_name: str | None = None,
    metadata_: dict | None = None,
    batch_id: UUID | None = None,
) -> FeedbackItem:
    """Create a single feedback item (manual or Slack)."""
    ts = _parse_timestamp(timestamp) if isinstance(timestamp, str) else timestamp
    item = FeedbackItem(
        org_id=org_id,
        content=content.strip(),
        source_type=source_type,
        source_id=source_id,
        timestamp=ts,
        author_email=author_email or None,
        author_name=author_name or None,
        organization_name=organization_name or None,
        metadata_=metadata_,
        batch_id=batch_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_feedback_items_batch(
    db: Session,
    org_id: UUID,
    batch_id: UUID,
    items: list[dict],
    *,
    source_id_prefix: str,
    start_row: int = 0,
) -> tuple[list[UUID], int]:
    """
    Insert multiple feedback items for a CSV batch. Each item dict must have
    at least "content". source_id is built as source_id_prefix + ":" + row_number
    (row_number = start_row + index). Skips duplicates (GAP 5 idempotency).
    Returns (list of created item UUIDs, skipped_duplicate_count).
    """
    created_ids: list[UUID] = []
    skipped = 0
    for i, row in enumerate(items):
        content = (row.get("content") or "").strip()
        if not content:
            continue
        row_number = start_row + i
        source_id = f"{source_id_prefix}:{row_number}"
        if check_duplicate(db, org_id, source_id):
            skipped += 1
            continue
        ts = row.get("timestamp")
        if isinstance(ts, str):
            ts = _parse_timestamp(ts)
        item = FeedbackItem(
            org_id=org_id,
            content=content,
            source_type="csv",
            source_id=source_id,
            timestamp=ts,
            author_email=row.get("author_email") or None,
            author_name=row.get("author_name") or None,
            organization_name=row.get("organization_name") or None,
            metadata_=row.get("metadata"),
            batch_id=batch_id,
        )
        db.add(item)
        db.flush()
        created_ids.append(item.id)
    db.commit()
    return created_ids, skipped


def get_feedback_items(
    db: Session,
    org_id: UUID,
    page: int = 1,
    page_size: int = 20,
    source_type_filter: str | None = None,
    match_status_filter: str | None = None,
    segment_filter: str | None = None,
    theme_id_filter: UUID | None = None,
    outliers_only: bool = False,
    unclustered_only: bool = False,
) -> tuple[list[FeedbackItem], int]:
    """List feedback items for org with pagination and optional filters."""
    q = db.query(FeedbackItem).options(joinedload(FeedbackItem.theme)).filter(FeedbackItem.org_id == org_id)
    if source_type_filter:
        q = q.filter(FeedbackItem.source_type == source_type_filter)
    if match_status_filter:
        q = q.filter(FeedbackItem.match_status == match_status_filter)
    if segment_filter:
        if segment_filter == "unmatched":
            q = q.filter((FeedbackItem.segment.is_(None)) | (FeedbackItem.segment == ""))
        else:
            q = q.filter(FeedbackItem.segment == segment_filter)
    if theme_id_filter is not None:
        q = q.filter(FeedbackItem.theme_id == theme_id_filter)
    if outliers_only:
        q = q.filter(FeedbackItem.is_outlier == True)
    if unclustered_only:
        q = q.filter(
            FeedbackItem.embedding.isnot(None),
            FeedbackItem.theme_id.is_(None),
            FeedbackItem.clustered_at.is_(None),
        )
    q = q.order_by(FeedbackItem.created_at.desc())
    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total


def get_feedback_item(db: Session, org_id: UUID, item_id: UUID) -> FeedbackItem | None:
    """Get a single feedback item by id; must belong to org_id."""
    return (
        db.query(FeedbackItem)
        .options(joinedload(FeedbackItem.theme))
        .filter(FeedbackItem.id == item_id, FeedbackItem.org_id == org_id)
        .first()
    )


def delete_feedback_item(db: Session, org_id: UUID, item_id: UUID) -> bool:
    """Delete a feedback item by id; must belong to org_id. Returns True if deleted."""
    item = get_feedback_item(db, org_id, item_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def get_enrichment_stats(db: Session, org_id: UUID) -> dict:
    """Return counts by match_status for org feedback items."""
    from sqlalchemy import func

    q = (
        db.query(FeedbackItem.match_status, func.count(FeedbackItem.id))
        .filter(FeedbackItem.org_id == org_id)
        .group_by(FeedbackItem.match_status)
    )
    counts = dict(q.all())
    total = sum(counts.values())
    return {
        "total": total,
        "matched": counts.get("matched", 0) + counts.get("auto_matched", 0),
        "pm_review": counts.get("pm_review", 0),
        "unmatched": counts.get("unmatched", 0),
    }


def get_pending_extraction_ids(db: Session, org_id: UUID) -> list[UUID]:
    """Return ids of feedback items with extraction_status pending or failed (for re-queue)."""
    rows = db.query(FeedbackItem.id).filter(
        FeedbackItem.org_id == org_id,
        FeedbackItem.extraction_status.in_(("pending", "failed")),
    ).all()
    return [r[0] for r in rows]
