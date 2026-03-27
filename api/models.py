"""
SQLAlchemy models for the media download service.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
import enum

from api.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MediaFormat(str, enum.Enum):
    VIDEO = "video"
    AUDIO = "audio"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2048), nullable=False, index=True)
    format = Column(SAEnum(MediaFormat), nullable=False, default=MediaFormat.VIDEO)
    quality = Column(String(20), nullable=False, default="best")
    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)

    # Media metadata (populated by worker after yt-dlp extract_info)
    title = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    thumbnail_url = Column(String(2048), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)

    # Storage
    s3_key = Column(String(1024), nullable=True)
    original_filename = Column(String(500), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Deduplication
    url_hash = Column(String(64), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Client info
    client_ip = Column(String(45), nullable=True)

    def __repr__(self):
        return f"<Job {self.id} [{self.status.value}] {self.url[:50]}>"
