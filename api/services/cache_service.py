"""
Redis cache service for job status, dedup, and metadata caching.
"""
import json
import hashlib
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import redis.asyncio as aioredis

from api.config import get_settings

settings = get_settings()

# Lazy-initialized Redis connection
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get or create async Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _redis


async def close_redis():
    """Close Redis connection on shutdown."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


# ─── URL Normalization & Dedup ───

# Query params to strip (tracking, non-essential)
STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "feature", "app", "src", "ref", "fbclid", "gclid", "si",
}


def normalize_url(url: str) -> str:
    """Normalize a URL to a canonical form for dedup hashing."""
    parsed = urlparse(url.strip().lower())

    # For youtu.be short links, extract video ID
    hostname = parsed.hostname or ""
    if hostname == "youtu.be":
        video_id = parsed.path.strip("/")
        return f"https://www.youtube.com/watch?v={video_id}"

    # Strip tracking params
    query = parse_qs(parsed.query, keep_blank_values=False)
    filtered = {k: v for k, v in query.items() if k not in STRIP_PARAMS}
    clean_query = urlencode(filtered, doseq=True)

    # Reconstruct with canonical scheme + host
    normalized = urlunparse((
        "https",
        "www.youtube.com" if "youtube.com" in hostname else hostname,
        parsed.path.rstrip("/"),
        "",
        clean_query,
        "",
    ))
    return normalized


def compute_url_hash(url: str, format: str, quality: str) -> str:
    """SHA-256 hash of normalized URL + format + quality for dedup."""
    normalized = normalize_url(url)
    key = f"{normalized}|{format}|{quality}"
    return hashlib.sha256(key.encode()).hexdigest()


async def check_dedup(url_hash: str) -> Optional[str]:
    """Check if a download for this URL+format+quality already exists.
    Returns existing job_id if found, None otherwise."""
    r = await get_redis()
    job_id = await r.get(f"dedup:{url_hash}")
    return job_id


async def set_dedup(url_hash: str, job_id: str, ttl_hours: int = 24):
    """Register a URL hash → job_id mapping for dedup."""
    r = await get_redis()
    await r.setex(f"dedup:{url_hash}", ttl_hours * 3600, str(job_id))


# ─── Job Progress ───

async def set_job_progress(job_id: str, progress: int):
    """Update job download progress (0-100)."""
    r = await get_redis()
    await r.setex(f"job:{job_id}:progress", 600, str(progress))


async def get_job_progress(job_id: str) -> Optional[int]:
    """Get current download progress."""
    r = await get_redis()
    val = await r.get(f"job:{job_id}:progress")
    return int(val) if val else None


async def get_playlist_progress(job_id: str) -> Optional[dict]:
    """Get playlist per-video progress state set by the worker."""
    r = await get_redis()
    val = await r.get(f"job:{job_id}:playlist")
    return json.loads(val) if val else None


# ─── Job Status Cache ───

async def cache_job_status(job_id: str, status: str, ttl: int = 30):
    """Cache job status for fast polling (short TTL)."""
    r = await get_redis()
    await r.setex(f"job:{job_id}:status", ttl, status)


async def get_cached_job_status(job_id: str) -> Optional[str]:
    """Get cached job status."""
    r = await get_redis()
    return await r.get(f"job:{job_id}:status")


# ─── Metadata Cache ───

async def cache_video_metadata(video_id: str, metadata: dict, ttl_hours: int = 6):
    """Cache video metadata to avoid repeated yt-dlp info extraction."""
    r = await get_redis()
    await r.setex(f"meta:{video_id}", ttl_hours * 3600, json.dumps(metadata))


async def get_cached_metadata(video_id: str) -> Optional[dict]:
    """Get cached video metadata."""
    r = await get_redis()
    data = await r.get(f"meta:{video_id}")
    return json.loads(data) if data else None


# ─── Rate Limiting ───

async def check_rate_limit(client_ip: str, limit_per_hour: int) -> tuple[bool, int]:
    """
    Sliding window rate limiter.
    Returns (allowed: bool, remaining: int).
    """
    import time
    r = await get_redis()
    key = f"rate:{client_ip}"
    now = time.time()
    window = 3600  # 1 hour

    pipe = r.pipeline()
    # Remove old entries outside the window
    pipe.zremrangebyscore(key, 0, now - window)
    # Add current request
    pipe.zadd(key, {str(now): now})
    # Count requests in window
    pipe.zcard(key)
    # Set expiry on the key
    pipe.expire(key, window)
    results = await pipe.execute()

    request_count = results[2]
    allowed = request_count <= limit_per_hour
    remaining = max(0, limit_per_hour - request_count)

    return allowed, remaining


# ─── Queue Depth ───

async def get_queue_depth() -> int:
    """Get approximate number of pending jobs in Celery queue."""
    r = await get_redis()
    depth = await r.llen("celery")
    return depth or 0
