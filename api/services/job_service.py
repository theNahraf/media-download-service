"""
Job service — business logic for creating, querying, and managing download jobs.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Job, JobStatus, MediaFormat
from api.schemas import JobCreateRequest
from api.services import cache_service
from api.config import get_settings

settings = get_settings()


async def create_job(
    db: AsyncSession,
    request: JobCreateRequest,
    client_ip: Optional[str] = None,
) -> tuple[Job, bool]:
    """
    Create a new download job or return existing one if dedup match.
    Returns (job, is_new).
    """
    # Compute dedup hash
    url_hash = cache_service.compute_url_hash(
        request.url, request.format.value, request.quality
    )

    # Check dedup cache
    existing_job_id = await cache_service.check_dedup(url_hash)
    if existing_job_id:
        existing_job = await get_job(db, UUID(existing_job_id))
        if existing_job and existing_job.status in (
            JobStatus.COMPLETED, JobStatus.PROCESSING, JobStatus.PENDING, JobStatus.UPLOADING
        ):
            return existing_job, False

    # Create new job
    job = Job(
        url=request.url,
        format=request.format,
        quality=request.quality,
        status=JobStatus.PENDING,
        url_hash=url_hash,
        client_ip=client_ip,
    )
    db.add(job)
    await db.flush()  # Get the auto-generated ID

    # Store dedup hash
    await cache_service.set_dedup(
        url_hash, str(job.id), ttl_hours=settings.download_expiry_hours
    )

    return job, True


async def get_job(db: AsyncSession, job_id: UUID) -> Optional[Job]:
    """Get a job by ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def cancel_job(db: AsyncSession, job_id: UUID) -> Optional[Job]:
    """Cancel a pending or processing job."""
    job = await get_job(db, job_id)
    if not job:
        return None

    if job.status in (JobStatus.PENDING, JobStatus.PROCESSING):
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(timezone.utc)
        await db.flush()

    return job


async def get_job_with_progress(db: AsyncSession, job_id: UUID) -> Optional[dict]:
    """Get job data enriched with real-time progress from Redis."""
    job = await get_job(db, job_id)
    if not job:
        return None

    progress = await cache_service.get_job_progress(str(job_id))

    result = {
        "job_id": job.id,
        "status": job.status,
        "progress": progress,
        "title": job.title,
        "duration_seconds": job.duration_seconds,
        "thumbnail_url": job.thumbnail_url,
        "file_size_bytes": job.file_size_bytes,
        "format": job.format,
        "quality": job.quality,
        "error_message": job.error_message,
        "retry_count": job.retry_count,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
        "download_url": None,
        "download_expires_at": None,
    }

    # Generate signed URL for completed jobs
    if job.status == JobStatus.COMPLETED and job.s3_key:
        from api.services.storage_service import generate_signed_url
        result["download_url"] = generate_signed_url(job.s3_key, download_filename=job.original_filename)
        result["download_expires_at"] = datetime.now(timezone.utc) + timedelta(
            seconds=settings.signed_url_expiry_seconds
        )

    return result
