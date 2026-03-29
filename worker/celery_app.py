"""
Celery worker configuration.
"""
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "media_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks", "worker.cleanup"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_transport_options={"visibility_timeout": 3600},
    # Run cleanup every 6 hours
    beat_schedule={
        "cleanup-expired-files": {
            "task": "worker.cleanup.cleanup_expired_files",
            "schedule": float(os.getenv("CLEANUP_INTERVAL_SECONDS", str(6 * 3600))),
        },
    },
)
