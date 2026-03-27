"""
Synchronous Redis client for Celery worker progress updates.
"""
import os
import redis

# Use env var directly to avoid loading async config settings in sync context unnecessarily
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def update_progress(job_id: str, process_percent: int):
    """Set job progress synchronously with expiration."""
    redis_client.setex(f"job:{job_id}:progress", 600, str(process_percent))
