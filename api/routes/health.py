"""
Health check endpoint — exposes system status for load balancers and monitoring.
"""
from fastapi import APIRouter
from api.schemas import HealthResponse
from api.services.cache_service import get_redis, get_queue_depth

router = APIRouter(tags=["Health"])


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns system component health status. Use for load balancer health checks.",
)
async def health_check():
    status = "healthy"
    redis_ok = False
    db_ok = False
    storage_ok = False
    queue_depth = 0

    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
        queue_depth = await get_queue_depth()
    except Exception:
        status = "degraded"

    # Check DB
    try:
        from api.database import async_session_factory
        from sqlalchemy import text
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        status = "degraded"

    # Check storage
    try:
        from api.services.storage_service import get_s3_client, ensure_bucket_exists
        from api.config import get_settings
        client = get_s3_client()
        client.head_bucket(Bucket=get_settings().s3_bucket_name)
        storage_ok = True
    except Exception:
        status = "degraded"

    return HealthResponse(
        status=status,
        queue_depth=queue_depth,
        db_connected=db_ok,
        redis_connected=redis_ok,
        storage_connected=storage_ok,
    )
