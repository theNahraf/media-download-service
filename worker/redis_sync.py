"""
Synchronous Redis client for Celery worker progress updates.
"""
import os
import json
import redis

# Use env var directly to avoid loading async config settings in sync context unnecessarily
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def update_progress(job_id: str, process_percent: int):
    """Set job progress synchronously with expiration."""
    redis_client.setex(f"job:{job_id}:progress", 600, str(process_percent))

def update_playlist_progress(job_id: str, current: int, total: int, current_title: str, bytes_downloaded: int = 0, bytes_total: int = 0):
    """Store playlist per-video download state in Redis."""
    data = json.dumps({
        "current": current,
        "total": total,
        "current_title": current_title,
        "bytes_downloaded": bytes_downloaded,
        "bytes_total": bytes_total,
    })
    redis_client.setex(f"job:{job_id}:playlist", 600, data)

def clear_playlist_progress(job_id: str):
    """Remove playlist progress key when done."""
    redis_client.delete(f"job:{job_id}:playlist")
