"""
Periodic cleanup task — deletes expired files from MinIO/R2 and marks jobs expired.
Runs automatically every DOWNLOAD_EXPIRY_HOURS (default 6h) via Celery Beat.
"""
import os
from datetime import datetime, timezone, timedelta
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app
from worker.db_sync import SessionLocal
from api.models import Job, JobStatus
from api.services.storage_service import delete_file
from sqlalchemy import update, select

logger = get_task_logger(__name__)

# How many hours until a completed file is deleted (default: 6 hours)
EXPIRY_HOURS = float(os.getenv("DOWNLOAD_EXPIRY_HOURS", "6"))


@celery_app.task(name="worker.cleanup.cleanup_expired_files")
def cleanup_expired_files():
    """
    Find all completed jobs older than EXPIRY_HOURS, delete their files
    from storage, and mark them as expired in the database.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=EXPIRY_HOURS)
    logger.info(f"Running cleanup — deleting files completed before {cutoff.isoformat()} ({EXPIRY_HOURS}h ago)")

    deleted_count = 0
    with SessionLocal() as db:
        # Find completed jobs with files that are past expiry
        jobs = db.execute(
            select(Job).where(
                Job.status == JobStatus.COMPLETED,
                Job.completed_at != None,
                Job.completed_at < cutoff,
                Job.s3_key != None,
            )
        ).scalars().all()

        for job in jobs:
            try:
                # Delete the file from MinIO / R2
                delete_file(job.s3_key)
                logger.info(f"Deleted {job.s3_key} for job {job.id}")
            except Exception as e:
                logger.warning(f"Could not delete {job.s3_key}: {e}")

            # Mark as expired regardless of delete success
            db.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(status=JobStatus.EXPIRED, s3_key=None)
            )
            deleted_count += 1

        db.commit()

    logger.info(f"Cleanup complete — {deleted_count} file(s) removed")
    return {"deleted": deleted_count}
