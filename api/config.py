"""
Application configuration — loaded from environment variables.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str

    # S3 / MinIO
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket_name: str
    s3_public_url: str

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Rate limiting
    rate_limit_per_hour: int = 30
    rate_limit_burst: int = 5

    # Download settings
    download_expiry_hours: int = 24
    signed_url_expiry_seconds: int = 3600
    max_file_size_mb: int = 5120
    max_download_timeout: int = 900

    # Worker
    worker_concurrency: int = 4

    # Admin Dashboard Auth
    admin_user: str = Field(default="admin", alias="FLOWER_USER")
    admin_password: str = Field(default="admin_secret_2026", alias="FLOWER_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
