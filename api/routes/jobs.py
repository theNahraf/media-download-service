"""
Job routes — CRUD operations for download jobs.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas import (
    JobCreateRequest,
    JobCreateResponse,
    JobStatusResponse,
    ErrorResponse,
)
from api.services import job_service, cache_service
from api.services.storage_service import generate_signed_url
from api.models import JobStatus
from api.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Create a download job",
    description="Submit a URL for async download. Returns immediately with a job ID for polling.",
)
async def create_job(
    request: JobCreateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Rate limiting
    client_ip = http_request.client.host if http_request.client else "unknown"
    allowed, remaining = await cache_service.check_rate_limit(
        client_ip, settings.rate_limit_per_hour
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again later.",
            headers={"Retry-After": "3600", "X-RateLimit-Remaining": "0"},
        )

    # Check backpressure — reject if queue is too deep
    queue_depth = await cache_service.get_queue_depth()
    if queue_depth > 10000:
        raise HTTPException(
            status_code=503,
            detail="Service is under heavy load. Please try again in a few minutes.",
            headers={"Retry-After": "120"},
        )

    # Create job (with dedup check)
    job, is_new = await job_service.create_job(db, request, client_ip=client_ip)

    # Enqueue to Celery if new
    if is_new:
        from worker.tasks import process_download
        process_download.delay(str(job.id))

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at,
        poll_url=f"/api/v1/jobs/{job.id}",
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Check job status",
    description="Poll this endpoint to track download progress and get the download URL when complete.",
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await job_service.get_job_with_progress(db, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(**result)


@router.get(
    "/{job_id}/download",
    summary="Download file (redirect)",
    description="Redirects to a signed S3 URL for direct download. Only works for completed jobs.",
    responses={
        302: {"description": "Redirect to signed download URL"},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def download_file(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed yet. Current status: {job.status.value}",
        )

    if not job.s3_key:
        raise HTTPException(status_code=404, detail="File not found in storage")

    signed_url = generate_signed_url(job.s3_key)
    return RedirectResponse(url=signed_url, status_code=302)


@router.delete(
    "/{job_id}",
    status_code=204,
    summary="Cancel a job",
    description="Cancel a pending or processing job. Completed files remain until lifecycle policy expires.",
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return None
