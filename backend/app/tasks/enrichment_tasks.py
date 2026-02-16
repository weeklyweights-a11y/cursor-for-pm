"""
Enrichment task: run customer matching for a single feedback item. Log errors; do not re-raise.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.feedback_item import FeedbackItem
from app.services import enrichment_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.enrichment_tasks.enrich_feedback_item_task")
def enrich_feedback_item_task(self, feedback_item_id: str, org_id: str) -> dict:
    """
    Enrich one feedback item (5-step matching). Catch and log errors; do not re-raise.
    """
    item_uuid = UUID(feedback_item_id)
    org_uuid = UUID(org_id)
    db: Session = SessionLocal()
    try:
        enrichment_service.enrich_feedback_item(db, org_uuid, item_uuid)
        item = db.query(FeedbackItem).filter(
            FeedbackItem.id == item_uuid,
            FeedbackItem.org_id == org_uuid,
        ).first()
        if item and (item.pain_point or "").strip() and item.embedding is None:
            from app.tasks.embedding_tasks import generate_embedding_task
            generate_embedding_task.delay(feedback_item_id, org_id)
        return {"status": "ok", "feedback_item_id": feedback_item_id}
    except Exception as e:
        logger.exception(
            "enrich_feedback_item_task failed feedback_item_id=%s org_id=%s",
            feedback_item_id,
            org_id,
        )
        return {"status": "failed", "feedback_item_id": feedback_item_id, "error": str(e)}
    finally:
        db.close()
