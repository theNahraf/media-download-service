"""
Admin route - Custom authentication & job dashboards.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.database import get_db
from api.models import Job, JobStatus
from api.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    if username == settings.admin_user and password == settings.admin_password:
        # Secure HttpOnly cookie
        response.set_cookie(
            key="admin_session", 
            value="authorized", 
            httponly=True, 
            samesite="lax",
            max_age=86400 * 7 # 1 week
        )
        return {"status": "success"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="admin_session")
    return {"status": "success"}

@router.get("/jobs")
async def get_all_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    if request.cookies.get("admin_session") != "authorized":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    result = await db.execute(select(Job).order_by(Job.created_at.desc()).limit(100))
    jobs = result.scalars().all()
    
    output = []
    for j in jobs:
        output.append({
            "id": j.id,
            "url": j.url,
            "status": j.status.value,
            "title": j.title,
            "created_at": j.created_at,
            "error_message": j.error_message
        })
    return output

@router.get("/metrics")
async def get_system_metrics(request: Request, db: AsyncSession = Depends(get_db)):
    if request.cookies.get("admin_session") != "authorized":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    stmt = select(Job.status, func.count(Job.id)).group_by(Job.status)
    result = await db.execute(stmt)
    counts = result.all()
    
    metrics = {"total": 0, "active": 0, "finished": 0}
    for status, count in counts:
        metrics["total"] += count
        if status.value in ["pending", "processing", "uploading"]:
            metrics["active"] += count
        else:
            metrics["finished"] += count
            
    return metrics

@router.delete("/jobs/{job_id}/purge")
async def purge_job_record(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    if request.cookies.get("admin_session") != "authorized":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Not found")
        
    await db.delete(job)
    await db.commit()
    return {"status": "success"}

@router.delete("/jobs/purge-failed")
async def purge_failed_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    if request.cookies.get("admin_session") != "authorized":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    stmt = select(Job).where(Job.status.in_([JobStatus.FAILED, JobStatus.CANCELLED]))
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    for job in jobs:
        await db.delete(job)
    await db.commit()
    return {"status": "success", "purged": len(jobs)}

@router.post("/jobs/cancel-active")
async def cancel_active_jobs(request: Request, db: AsyncSession = Depends(get_db)):
    if request.cookies.get("admin_session") != "authorized":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    stmt = select(Job).where(Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.UPLOADING]))
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    from worker.celery_app import celery_app
    from datetime import datetime, timezone
    
    count = 0
    for job in jobs:
        celery_app.control.revoke(str(job.id), terminate=True, signal='SIGKILL')
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(timezone.utc)
        count += 1
    
    await db.commit()
    return {"status": "success", "cancelled": count}
