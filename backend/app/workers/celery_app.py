from celery import Celery

from app.config import settings

celery_app = Celery(
    "llm_intel_worker",
    broker=settings.default_celery_broker_url,
    backend=settings.default_celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Route specific tasks to specific queues if needed
    task_routes={
        "app.workers.metrics_worker.process_call": {"queue": "metrics"},
    }
)

# Autodiscover tasks from the specific worker modules
celery_app.autodiscover_tasks(["app.workers.metrics_worker"])
