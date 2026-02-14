"""Embedding task: generate embedding for one feedback item; optionally queue clustering."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.feedback_item import FeedbackItem
from app.services import embedding_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.embedding_tasks.generate_embedding_task")
def generate_embedding_task(self, feedback_item_id: str, org_id: str) -> dict:
    """
    Generate embedding for one feedback item. After storing, check should_recluster
    and queue run_clustering_task if threshold met. Log errors; do not re-raise.
    """
    item_uuid = UUID(feedback_item_id)
    org_uuid = UUID(org_id)
    db: Session = SessionLocal()
    try:
        item = db.query(FeedbackItem).filter(
            FeedbackItem.id == item_uuid,
            FeedbackItem.org_id == org_uuid,
        ).first()
        if not item:
            logger.warning("generate_embedding_task: item not found id=%s", feedback_item_id)
            return {"status": "skipped", "feedback_item_id": feedback_item_id}
        text = (item.pain_point or "").strip() or (item.content or "").strip()
        vec = embedding_service.generate_embedding(text)
        if vec is None:
            return {"status": "skipped", "feedback_item_id": feedback_item_id}
        item.embedding = vec
        db.commit()
        from app.services.clustering_service import should_recluster

        if should_recluster(db, org_uuid):
            from app.tasks.clustering_tasks import run_clustering_task

            run_clustering_task.delay(str(org_id))
        return {"status": "ok", "feedback_item_id": feedback_item_id}
    except Exception as e:
        logger.exception(
            "generate_embedding_task failed feedback_item_id=%s org_id=%s",
            feedback_item_id,
            org_id,
        )
        return {"status": "failed", "feedback_item_id": feedback_item_id, "error": str(e)}
    finally:
        db.close()
