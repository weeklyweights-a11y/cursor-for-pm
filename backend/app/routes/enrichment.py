from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user_dependency
from app.models.user import User
from app.schemas.enrichment import ReEnrichResponse
from app.services import enrichment_service
from app.tasks.enrichment_tasks import enrich_feedback_item_task

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/re-enrich")
def re_enrich_unmatched(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
) -> dict:
    """Queue enrichment for all unmatched items with extraction completed."""
    pairs = enrichment_service.re_enrich_unmatched(db, current_user.org_id)
    for feedback_item_id, org_id in pairs:
        enrich_feedback_item_task.delay(str(feedback_item_id), str(org_id))
    return {"data": ReEnrichResponse(items_queued=len(pairs)).model_dump()}
