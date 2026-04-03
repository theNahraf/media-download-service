"""
Celery worker configuration.
"""
import os
import ssl
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "media_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks", "worker.cleanup"]
)

# Enable TLS if using Upstash (rediss:// protocol)
_redis_ssl = REDIS_URL.startswith("rediss://")

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_transport_options={"visibility_timeout": 3600},
    # SSL settings for Upstash Redis
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE} if _redis_ssl else None,
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE} if _redis_ssl else None,
    # Run cleanup every 6 hours
    beat_schedule={
        "cleanup-expired-files": {
            "task": "worker.cleanup.cleanup_expired_files",
            "schedule": float(os.getenv("CLEANUP_INTERVAL_SECONDS", str(6 * 3600))),
        },
    },
)
