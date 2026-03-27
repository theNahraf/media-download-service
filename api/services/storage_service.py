"""
S3/MinIO storage service — handles file uploads and signed URL generation.
"""
import io
from typing import Optional
from datetime import timedelta
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from api.config import get_settings

settings = get_settings()

# Lazy-initialized S3 client
_s3_client = None


def get_s3_client():
    """Get or create S3 client (MinIO-compatible)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
            region_name="us-east-1",
        )
    return _s3_client


def ensure_bucket_exists():
    """Create the download bucket and make it public."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket_name)
    except ClientError:
        client.create_bucket(Bucket=settings.s3_bucket_name)
        
    # Make the bucket completely public for downloads
    import json
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{settings.s3_bucket_name}/*"]
            }
        ]
    }
    try:
        client.put_bucket_policy(Bucket=settings.s3_bucket_name, Policy=json.dumps(policy))
    except ClientError as e:
        print(f"Policy error: {e}")

    # Set lifecycle policy: auto-delete after 24 hours
    try:
        client.put_bucket_lifecycle_configuration(
            Bucket=settings.s3_bucket_name,
            LifecycleConfiguration={
                "Rules": [
                    {
                        "ID": "expire-downloads",
                        "Filter": {"Prefix": "downloads/"},
                        "Status": "Enabled",
                        "Expiration": {"Days": 1},
                    }
                ]
            },
        )
    except ClientError:
        pass


def upload_file(
    file_path: str,
    s3_key: str,
    content_type: str = "application/octet-stream",
    original_filename: str = None
) -> str:
    """
    Upload a local file to S3/MinIO with the specified content disposition.
    Returns the S3 key.
    """
    client = get_s3_client()
    extra_args = {"ContentType": content_type}
    
    if original_filename:
        import urllib.parse
        encoded_name = urllib.parse.quote(original_filename)
        extra_args["ContentDisposition"] = f"attachment; filename*=UTF-8''{encoded_name}"
        
    client.upload_file(
        file_path,
        settings.s3_bucket_name,
        s3_key,
        ExtraArgs=extra_args,
    )
    return s3_key


def upload_bytes(
    data: bytes,
    s3_key: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload raw bytes to S3/MinIO."""
    client = get_s3_client()
    client.upload_fileobj(
        io.BytesIO(data),
        settings.s3_bucket_name,
        s3_key,
        ExtraArgs={"ContentType": content_type},
    )
    return s3_key


import urllib.parse

def generate_signed_url(s3_key: str, expiry_seconds: Optional[int] = None, download_filename: Optional[str] = None) -> str:
    """
    Returns the direct public URL for downloading a file, completely bypassing presigned signatures.
    """
    # Simply format the URL based on the public server IP!
    base = settings.s3_public_url.rstrip("/")
    return f"{base}/{settings.s3_bucket_name}/{s3_key}"


def delete_file(s3_key: str):
    """Delete a file from S3/MinIO."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
    except ClientError:
        pass


def file_exists(s3_key: str) -> bool:
    """Check if a file exists in S3/MinIO."""
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return True
    except ClientError:
        return False
