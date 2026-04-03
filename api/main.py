"""
FastAPI application — entry point for the API service.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.database import init_db, close_db
from api.services.cache_service import close_redis
from api.services.storage_service import ensure_bucket_exists
from api.routes.jobs import router as jobs_router
from api.routes.health import router as health_router
from api.routes.admin import router as admin_router
from api.routes.preview import router as preview_router
from api.middleware.rate_limiter import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──
    logger.info("🚀 Starting Media Download Service API...")

    # Initialize database tables
    await init_db()
    logger.info("✅ Database initialized")

    # Ensure Google Drive folder is accessible
    try:
        ensure_bucket_exists()
        logger.info("✅ Google Drive storage ready")
    except Exception as e:
        logger.warning(f"⚠️  Google Drive check failed (will retry): {e}")

    logger.info("✅ API ready to accept requests")

    yield

    # ── Shutdown ──
    logger.info("🛑 Shutting down...")
    await close_redis()
    await close_db()
    logger.info("✅ Shutdown complete")


# ── Create FastAPI App ──
app = FastAPI(
    title="Media Download Service",
    description=(
        "A scalable, async media download service. "
        "Submit URLs for background downloading, track progress, "
        "and retrieve files via signed URLs."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# ── Routes ──
app.include_router(jobs_router)
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(preview_router)

# ── Static Files & Frontend ──
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend SPA."""
    return FileResponse("frontend/index.html")

@app.get("/adminuser", include_in_schema=False)
async def serve_admin_frontend():
    """Serve the Custom Admin Dashboard."""
    return FileResponse("frontend/admin.html")

@app.get("/{path:path}", include_in_schema=False)
async def catch_all_frontend(path: str):
    """Catch-all route to serve frontend for the URL redirect feature."""
    return FileResponse("frontend/index.html")
