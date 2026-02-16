"""Brief generation Celery task (Phase 7)."""

from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services import brief_generation_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True)
def generate_brief_task(self, brief_id: str, org_id: str, theme_id: str) -> None:
    """Generate all sections for a brief; set status completed or failed."""
    db = SessionLocal()
    try:
        brief_generation_service.generate_all_sections(
            db, UUID(org_id), UUID(brief_id), UUID(theme_id)
        )
    except Exception as e:
        logger.error(
            "generate_brief_task failed",
            extra={"brief_id": brief_id, "org_id": org_id, "theme_id": theme_id, "error": str(e)},
        )
        from app.models.brief import Brief
        brief = db.query(Brief).filter(Brief.id == UUID(brief_id), Brief.org_id == UUID(org_id)).first()
        if brief:
            brief.status = "failed"
            db.commit()
    finally:
        db.close()
