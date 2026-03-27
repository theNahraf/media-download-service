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
    include=["worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Visibility timeout for unacknowledged tasks (e.g. if worker crashes)
    broker_transport_options={"visibility_timeout": 3600}, # 1 hour
    # Worker concurrency is controlled via command line options or env var
    # usually: celery -A worker.celery_app worker --concurrency=4
)
