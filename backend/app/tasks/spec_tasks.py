"""Spec generation Celery task (Phase 8)."""

from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services import spec_generation_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True)
def generate_spec_task(
    self, spec_id: str, org_id: str, brief_id: str, config: dict
) -> None:
    """Generate all sections for a spec; set status completed or failed."""
    db = SessionLocal()
    try:
        spec_generation_service.generate_all_sections(
            db,
            UUID(org_id),
            UUID(spec_id),
            UUID(brief_id),
            config or {},
        )
    except Exception as e:
        logger.error(
            "generate_spec_task failed",
            extra={
                "spec_id": spec_id,
                "org_id": org_id,
                "brief_id": brief_id,
                "error": str(e),
            },
        )
        from app.models.spec import Spec

        spec = (
            db.query(Spec)
            .filter(Spec.id == UUID(spec_id), Spec.org_id == UUID(org_id))
            .first()
        )
        if spec:
            spec.status = "failed"
            db.commit()
    finally:
        db.close()
