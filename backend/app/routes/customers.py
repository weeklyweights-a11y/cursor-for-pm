import io
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.customer import (
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUploadResponse,
    TopCustomerResponse,
)
from app.schemas.feedback import pagination_meta
from app.services import customer_service, enrichment_service
from app.tasks.enrichment_tasks import enrich_feedback_item_task

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/upload")
async def upload_customers_csv(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """Upload customer CSV. Required column: domain (or website, url, email_domain)."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .csv file.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty.",
        )
    content_bytes = content
    if content_bytes.startswith(b"\xef\xbb\xbf"):
        content_bytes = content_bytes[3:]
    try:
        df = pd.read_csv(io.BytesIO(content_bytes), header=0, encoding="utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV: {str(e)[:200]}",
        ) from e
    headers = [str(h).strip() for h in df.columns]
    mapping = customer_service.detect_customer_csv_columns(headers)
    if "domain" not in mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect domain column. Use: domain, website, url, or email_domain.",
        )
    try:
        result = customer_service.upload_customers_csv(
            db, current_user.org_id, content_bytes, column_mapping=mapping
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        from app.utils.logging import get_logger
        get_logger(__name__).exception("Customer CSV upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Check server logs.",
        ) from e
    pairs = enrichment_service.re_enrich_unmatched(db, current_user.org_id)
    for feedback_item_id, org_id in pairs:
        enrich_feedback_item_task.delay(str(feedback_item_id), str(org_id))
    response = CustomerUploadResponse(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        items_queued=len(pairs),
    )
    return {"data": response.model_dump()}


@router.get("")
def list_customers(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
    segment: str | None = None,
    search: str | None = None,
) -> dict:
    """List customers; paginated, optional segment and search."""
    items, total = customer_service.get_customers(
        db,
        current_user.org_id,
        page=page,
        page_size=page_size,
        segment_filter=segment,
        search=search,
    )
    data = []
    for c in items:
        meta_val = getattr(c, "metadata_", None)
        meta_val = dict(meta_val) if meta_val and hasattr(meta_val, "items") else (meta_val if isinstance(meta_val, dict) else None)
        data.append(
            CustomerResponse(
                id=c.id,
                org_id=c.org_id,
                domain=c.domain,
                company_name=c.company_name,
                segment=c.segment,
                metadata=meta_val,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
            ).model_dump()
        )
    return {"data": data, "pagination": pagination_meta(page, page_size, total)}


@router.get("/top")
def get_top_customers(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
    limit: int = 5,
) -> dict:
    """Top customers by feedback count (for dashboard card)."""
    pairs = customer_service.get_top_customers(db, current_user.org_id, limit=limit)
    data = [
        {
            **TopCustomerResponse(
                id=c.id,
                domain=c.domain,
                company_name=c.company_name,
                feedback_count=count,
            ).model_dump(),
            "metadata": getattr(c, "metadata_", None),
        }
        for c, count in pairs
    ]
    return {"data": data}


@router.get("/{customer_id}")
def get_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Get single customer with feedback stats."""
    customer = customer_service.get_customer(db, current_user.org_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    count, by_source, latest = customer_service.get_customer_feedback_stats(
        db, current_user.org_id, customer_id
    )
    meta_val = getattr(customer, "metadata_", None)
    meta_val = dict(meta_val) if meta_val and hasattr(meta_val, "items") else (meta_val if isinstance(meta_val, dict) else None)
    base = CustomerResponse(
        id=customer.id,
        org_id=customer.org_id,
        domain=customer.domain,
        company_name=customer.company_name,
        segment=customer.segment,
        metadata=meta_val,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    ).model_dump()
    detail = CustomerDetailResponse(
        **base,
        feedback_count=count,
        feedback_by_source=by_source,
        latest_feedback_date=latest,
    )
    return {"data": detail.model_dump()}


@router.delete("/{customer_id}")
def deactivate_customer(
    customer_id: UUID,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Soft-deactivate customer."""
    if not customer_service.deactivate_customer(db, current_user.org_id, customer_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return {"data": {"status": "deactivated"}}
