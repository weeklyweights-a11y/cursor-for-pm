"""Celery app for async CSV and Slack processing."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "cursor_for_pms",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.csv_tasks",
        "app.tasks.slack_tasks",
        "app.tasks.extraction_tasks",
        "app.tasks.enrichment_tasks",
        "app.tasks.embedding_tasks",
        "app.tasks.clustering_tasks",
    ],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
