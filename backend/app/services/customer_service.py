"""
Customer CRUD and CSV upload. All operations are org-scoped.
"""

import io
from uuid import UUID

import pandas as pd
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.feedback_item import FeedbackItem
from app.schemas.customer import CustomerUploadResponse
from app.utils.domain import normalize_domain
from app.utils.logging import get_logger

logger = get_logger(__name__)

_DOMAIN_KEYWORDS = frozenset(
    {"domain", "website", "url", "email_domain", "company_domain", "customer_domain"}
)
_COMPANY_NAME_KEYWORDS = frozenset(
    {"company_name", "name", "company", "account", "customer", "organization", "org_name"}
)
_SEGMENT_KEYWORDS = frozenset({"segment", "tier", "plan", "size", "customer_type"})


def detect_customer_csv_columns(headers: list[str]) -> dict[str, int]:
    """
    Map customer CSV fields to column indices (case-insensitive).
    Domain is required. Returns e.g. {"domain": 0, "company_name": 1, "segment": 2}.
    """
    normalized = [h.strip().lower() for h in headers]
    mapping: dict[str, int] = {}
    for keywords, field in [
        (_DOMAIN_KEYWORDS, "domain"),
        (_COMPANY_NAME_KEYWORDS, "company_name"),
        (_SEGMENT_KEYWORDS, "segment"),
    ]:
        for idx, h in enumerate(normalized):
            if h in keywords:
                mapping[field] = idx
                break
    return mapping


def upload_customers_csv(
    db: Session, org_id: UUID, file_content: bytes, column_mapping: dict[str, int] | None = None
) -> CustomerUploadResponse:
    """
    Parse customer CSV and upsert by (org_id, domain). Normalizes domain.
    Returns counts: created, updated, skipped (e.g. empty domain).
    """
    content = file_content
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]
    df = pd.read_csv(io.BytesIO(content), header=0, dtype=str, keep_default_na=False, encoding="utf-8")
    headers = [str(h).strip() for h in df.columns]
    mapping = column_mapping or detect_customer_csv_columns(headers)
    if "domain" not in mapping:
        raise ValueError("Could not detect domain column. Use header: domain, website, url, or email_domain.")

    used_indices = set(mapping.values())
    created, updated, skipped = 0, 0, 0
    for row in df.values.tolist():
        domain_val = row[mapping["domain"]].strip() if mapping["domain"] < len(row) else ""
        domain = normalize_domain(domain_val)
        if not domain:
            skipped += 1
            continue
        company_name = None
        if "company_name" in mapping and mapping["company_name"] < len(row):
            company_name = (row[mapping["company_name"]] or "").strip() or None
        segment_val = None
        if "segment" in mapping and mapping["segment"] < len(row):
            segment_val = (row[mapping["segment"]] or "").strip().lower().replace("-", "_") or None
        if segment_val and segment_val not in ("smb", "mid_market", "enterprise"):
            segment_val = None

        metadata: dict[str, str] = {}
        for idx, header in enumerate(headers):
            if idx not in used_indices and idx < len(row):
                val = (row[idx] or "").strip()
                if val:
                    metadata[header.strip()] = val

        existing = (
            db.query(Customer)
            .filter(Customer.org_id == org_id, Customer.domain == domain)
            .first()
        )
        if existing:
            existing.company_name = company_name or existing.company_name
            existing.segment = segment_val or existing.segment
            existing.is_active = True
            if metadata:
                existing.metadata_ = metadata
            db.flush()
            updated += 1
        else:
            db.add(
                Customer(
                    org_id=org_id,
                    domain=domain,
                    company_name=company_name,
                    segment=segment_val,
                    metadata_=metadata or None,
                    is_active=True,
                )
            )
            db.flush()
            created += 1
    db.commit()
    logger.info(
        "Customer CSV upload",
        extra={
            "org_id": str(org_id),
            "rows_created": created,
            "rows_updated": updated,
            "rows_skipped": skipped,
        },
    )
    return CustomerUploadResponse(created=created, updated=updated, skipped=skipped)


def get_customers(
    db: Session,
    org_id: UUID,
    page: int = 1,
    page_size: int = 20,
    segment_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[Customer], int]:
    """List customers for org with pagination, optional segment and domain/company_name search."""
    q = db.query(Customer).filter(Customer.org_id == org_id, Customer.is_active == True)
    if segment_filter:
        q = q.filter(Customer.segment == segment_filter)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(Customer.domain).like(term),
                func.lower(Customer.company_name or "").like(term),
            )
        )
    q = q.order_by(Customer.domain)
    total = q.count()
    offset = (page - 1) * page_size
    items = q.offset(offset).limit(page_size).all()
    return items, total


def get_customer(db: Session, org_id: UUID, customer_id: UUID) -> Customer | None:
    """Get a single customer by id; must belong to org_id."""
    return db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.org_id == org_id,
    ).first()


def get_customer_feedback_stats(
    db: Session, org_id: UUID, customer_id: UUID
) -> tuple[int, dict[str, int], object]:
    """
    Returns (feedback_count, feedback_by_source, latest_feedback_date) for a customer.
    feedback_by_source is e.g. {"csv": 5, "slack": 2}. latest_feedback_date is max(timestamp).
    """
    q = db.query(
        FeedbackItem.source_type,
        func.count(FeedbackItem.id).label("cnt"),
    ).filter(
        FeedbackItem.org_id == org_id,
        FeedbackItem.customer_id == customer_id,
    ).group_by(FeedbackItem.source_type)
    rows = q.all()
    total = sum(r.cnt for r in rows)
    by_source = {r.source_type: r.cnt for r in rows}
    latest_row = (
        db.query(func.max(FeedbackItem.timestamp))
        .filter(FeedbackItem.org_id == org_id, FeedbackItem.customer_id == customer_id)
        .scalar()
    )
    return total, by_source, latest_row


def get_top_customers(
    db: Session, org_id: UUID, limit: int = 5
) -> list[tuple[Customer, int]]:
    """
    Top N customers by feedback count. Returns list of (Customer, feedback_count).
    Only includes customers with at least one feedback item.
    """
    subq = (
        db.query(FeedbackItem.customer_id, func.count(FeedbackItem.id).label("cnt"))
        .filter(
            FeedbackItem.org_id == org_id,
            FeedbackItem.customer_id.isnot(None),
        )
        .group_by(FeedbackItem.customer_id)
        .subquery()
    )
    rows = (
        db.query(Customer, subq.c.cnt)
        .join(subq, Customer.id == subq.c.customer_id)
        .filter(Customer.org_id == org_id, Customer.is_active == True)
        .order_by(subq.c.cnt.desc())
        .limit(limit)
        .all()
    )
    return [(c, int(cnt)) for c, cnt in rows]


def deactivate_customer(db: Session, org_id: UUID, customer_id: UUID) -> bool:
    """Soft-deactivate customer. Returns True if found and updated."""
    customer = get_customer(db, org_id, customer_id)
    if not customer:
        return False
    customer.is_active = False
    db.commit()
    return True
