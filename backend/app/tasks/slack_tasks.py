"""
Process Slack event in background. GAP 5: idempotent via check_duplicate inside process_slack_message.
"""

import logging
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services import slack_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.slack_tasks.process_slack_event")
def process_slack_event(self, org_id: str, event_data: dict) -> dict:
    """
    Process one Slack message event. slack_service.process_slack_message applies
    GAP 2 filters and check_duplicate (GAP 5); running twice does not create duplicates.
    """
    org_uuid = UUID(org_id)
    db = SessionLocal()
    try:
        created_item = slack_service.process_slack_message(db, org_uuid, event_data)
        if created_item is not None:
            from app.tasks.extraction_tasks import extract_feedback_signals
            extract_feedback_signals.delay(str(created_item.id), org_id)
        return {"processed": True, "created": created_item is not None}
    except Exception as e:
        logger.exception("process_slack_event failed org_id=%s", org_id)
        return {"processed": False, "error": str(e)}
    finally:
        db.close()
