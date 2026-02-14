from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.feedback_item import FeedbackItem
from app.models.user import User
from app.schemas.clustering import ClusteringStatusResponse
from app.services import clustering_service
from app.tasks.clustering_tasks import run_clustering_task
from app.tasks.embedding_tasks import generate_embedding_task

router = APIRouter(prefix="/clustering", tags=["clustering"])


@router.post("/backfill-embeddings")
def backfill_embeddings(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Queue embedding generation for all feedback items that have pain_point but no embedding."""
    items = (
        db.query(FeedbackItem.id)
        .filter(
            FeedbackItem.org_id == current_user.org_id,
            FeedbackItem.embedding.is_(None),
            FeedbackItem.pain_point.isnot(None),
            FeedbackItem.pain_point != "",
        )
        .all()
    )
    org_id_str = str(current_user.org_id)
    for (item_id,) in items:
        generate_embedding_task.delay(str(item_id), org_id_str)
    return {"data": {"enqueued": len(items)}}


@router.post("/run")
def run_clustering(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Enqueue clustering task; return 202 with status."""
    run_clustering_task.delay(str(current_user.org_id))
    status_resp = clustering_service.get_clustering_status(db, current_user.org_id)
    return {"data": {"status": "enqueued", "clustering": ClusteringStatusResponse.model_validate(status_resp).model_dump()}}


@router.get("/status")
def get_clustering_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Return is_running, last_run_at, last_run_result, items_pending."""
    status_resp = clustering_service.get_clustering_status(db, current_user.org_id)
    return {"data": ClusteringStatusResponse.model_validate(status_resp).model_dump()}
