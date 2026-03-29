"""
Pydantic schemas for request validation and response serialization.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse

from api.models import JobStatus, MediaFormat


# ─── Allowed domains for URL validation ───
ALLOWED_DOMAINS = {
    "youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com", "music.youtube.com",
    "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "facebook.com", "www.facebook.com", "fb.watch",
    "reddit.com", "www.reddit.com",
    "vimeo.com", "www.vimeo.com",
    "twitch.tv", "www.twitch.tv"
}


# ─── Request Schemas ───

class JobCreateRequest(BaseModel):
    url: str = Field(..., max_length=2048, description="Media URL to download")
    format: MediaFormat = Field(default=MediaFormat.VIDEO, description="Output format: video or audio")
    quality: str = Field(default="best", description="Quality: 360p, 480p, 720p, 1080p, best")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")

        parsed = urlparse(v)

        # Must be HTTPS
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP/HTTPS URLs are supported")

        # Domain allowlist
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_DOMAINS:
            raise ValueError(
                f"Unsupported platform: {hostname}. "
                f"Supported: {', '.join(sorted(ALLOWED_DOMAINS))}"
            )

        return v

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        allowed = {"360p", "480p", "720p", "1080p", "best"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"Quality must be one of: {', '.join(sorted(allowed))}")
        return v


# ─── Response Schemas ───

class JobCreateResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime
    poll_url: str

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    progress: Optional[int] = None
    title: Optional[str] = None
    duration_seconds: Optional[int] = None
    thumbnail_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    format: MediaFormat
    quality: str
    error_message: Optional[str] = None
    retry_count: int = 0
    download_url: Optional[str] = None
    download_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    queue_depth: int = 0
    active_workers: int = 0
    db_connected: bool = False
    redis_connected: bool = False
    storage_connected: bool = False


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
