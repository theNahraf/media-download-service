"""
Synchronous DB helpers for the Celery worker.
The worker runs synchronously, so we use psycopg2 or standard psycopg.
"""
import os
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from api.models import Job, JobStatus
from api.config import get_settings

settings = get_settings()

# We need a synchronous database URL for Celery workers
sync_db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql")
if "://" not in sync_db_url:
    # Fallback if env var doesn't contain driver
    sync_db_url = os.getenv("DATABASE_URL", "postgresql://mediadown:change_me_in_production@localhost:5432/mediadownload").replace("+asyncpg", "")

engine = create_engine(sync_db_url, pool_size=10, max_overflow=5)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_job_status(job_id: str, status: JobStatus, **kwargs):
    """Update job status and optionally other fields."""
    with SessionLocal() as db:
        stmt = update(Job).where(Job.id == job_id).values(status=status, **kwargs)
        db.execute(stmt)
        db.commit()

def mark_job_failed(job_id: str, error_message: str):
    """Mark a job as failed and record the error."""
    with SessionLocal() as db:
        # Increment retry_count and check if we should still retry... handled by Celery usually
        # but we mark permanent failure here
        stmt = update(Job).where(Job.id == job_id).values(
            status=JobStatus.FAILED, 
            error_message=str(error_message)[:2000] # Truncate to fit column
        )
        db.execute(stmt)
        db.commit()

def update_job_metadata(job_id: str, metadata: dict):
    """Update job with yt-dlp extracted metadata."""
    with SessionLocal() as db:
        stmt = update(Job).where(Job.id == job_id).values(
            title=metadata.get("title", "")[:500],
            duration_seconds=metadata.get("duration"),
            thumbnail_url=metadata.get("thumbnail", "")[:2048]
        )
        db.execute(stmt)
        db.commit()

def increment_retry_count(job_id: str):
    """Increment retry count for a job."""
    with SessionLocal() as db:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.retry_count += 1
            db.commit()
