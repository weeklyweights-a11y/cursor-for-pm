"""
Extraction task: run signal extraction for a single feedback item. On exception log and set failed.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.feedback_item import FeedbackItem
from app.services import extraction_service
from app.tasks.enrichment_tasks import enrich_feedback_item_task

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.extraction_tasks.extract_feedback_signals")
def extract_feedback_signals(self, feedback_item_id: str, org_id: str) -> dict:
    """
    Extract signals for one feedback item. On exception log and set extraction_status to failed;
    do not re-raise.
    """
    item_uuid = UUID(feedback_item_id)
    org_uuid = UUID(org_id)
    db: Session = SessionLocal()
    try:
        extraction_service.extract_signals(db, item_uuid, org_uuid)
        enrich_feedback_item_task.delay(feedback_item_id, org_id)
        return {"status": "ok", "feedback_item_id": feedback_item_id}
    except Exception as e:
        logger.exception("extract_feedback_signals failed feedback_item_id=%s org_id=%s", feedback_item_id, org_id)
        try:
            item = db.query(FeedbackItem).filter(
                FeedbackItem.id == item_uuid,
                FeedbackItem.org_id == org_uuid,
            ).first()
            if item:
                item.extraction_status = "failed"
                item.raw_llm_response = (str(e)[:10000] if str(e) else None)
                db.commit()
        except Exception:
            pass
        return {"status": "failed", "feedback_item_id": feedback_item_id, "error": str(e)}
    finally:
        db.close()
