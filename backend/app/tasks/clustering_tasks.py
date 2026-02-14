"""Clustering task: run HDBSCAN clustering for an org."""

import logging
from uuid import UUID

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.clustering_service import run_clustering, set_clustering_running

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.clustering_tasks.run_clustering_task")
def run_clustering_task(self, org_id: str) -> dict:
    """Set running, run clustering, clear running. On exception clear running and log."""
    org_uuid = UUID(org_id)
    set_clustering_running(org_uuid, True)
    db = SessionLocal()
    try:
        result = run_clustering(db, org_uuid)
        return {"status": "ok", "org_id": org_id, "result": result}
    except Exception as e:
        logger.exception("run_clustering_task failed org_id=%s", org_id)
        return {"status": "failed", "org_id": org_id, "error": str(e)}
    finally:
        set_clustering_running(org_uuid, False)
        db.close()
