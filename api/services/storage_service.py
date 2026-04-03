"""
Google Drive storage service — handles file uploads and download URL generation
using OAuth2 credentials (refresh token) so files are owned by your personal
Google account and count against your 5TB quota.
"""
import io
import os
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

from api.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Scopes required for uploading, deleting, and sharing files
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Lazy-initialized Drive service
_drive_service = None


def _get_credentials():
    """
    Build OAuth2 credentials from the refresh token stored in environment variables.
    The refresh token was generated once via setup_gdrive_oauth.py.
    """
    creds = Credentials(
        token=None,  # Will be refreshed automatically
        refresh_token=settings.gdrive_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gdrive_client_id,
        client_secret=settings.gdrive_client_secret,
        scopes=SCOPES,
    )
    # Force a token refresh to get a valid access token
    creds.refresh(Request())
    return creds


def get_drive_service():
    """Get or create the authenticated Google Drive API service."""
    global _drive_service
    if _drive_service is None:
        credentials = _get_credentials()
        _drive_service = build(
            "drive", "v3", credentials=credentials, cache_discovery=False
        )
    return _drive_service


def ensure_bucket_exists():
    """
    Verify that the configured Google Drive folder exists and is accessible.
    Equivalent of the old ensure_bucket_exists().
    """
    service = get_drive_service()
    folder_id = settings.gdrive_folder_id
    try:
        meta = service.files().get(fileId=folder_id, fields="id, name").execute()
        logger.info(
            f"✅ Google Drive folder verified: '{meta.get('name')}' ({folder_id})"
        )
    except HttpError as e:
        raise RuntimeError(
            f"Cannot access Google Drive folder {folder_id}. Error: {e}"
        )


def upload_file(
    file_path: str,
    s3_key: str,
    content_type: str = "application/octet-stream",
    original_filename: str = None,
) -> str:
    """
    Upload a local file to Google Drive inside the configured folder.
    Returns the Google Drive file ID (stored in the DB's s3_key column).
    """
    service = get_drive_service()

    # Use original filename if provided, else derive from s3_key
    name = original_filename or os.path.basename(s3_key)

    file_metadata = {
        "name": name,
        "parents": [settings.gdrive_folder_id],
    }

    media = MediaFileUpload(
        file_path,
        mimetype=content_type,
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10 MB chunks for large files
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    file_id = file.get("id")
    logger.info(f"Uploaded '{name}' to Google Drive → file ID: {file_id}")

    # Make file publicly accessible (anyone with link can download)
    _make_public(file_id)

    return file_id


def upload_bytes(
    data: bytes,
    s3_key: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload raw bytes to Google Drive."""
    service = get_drive_service()

    name = os.path.basename(s3_key)
    file_metadata = {
        "name": name,
        "parents": [settings.gdrive_folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(data),
        mimetype=content_type,
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    file_id = file.get("id")
    _make_public(file_id)
    return file_id


def generate_signed_url(
    s3_key: str,
    expiry_seconds: Optional[int] = None,
    download_filename: Optional[str] = None,
) -> str:
    """
    Generate a direct download URL for a Google Drive file.
    The s3_key parameter is actually the Google Drive file ID.
    Uses confirm=t to bypass the virus-scan warning for large files.
    """
    file_id = s3_key
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    return url


def delete_file(s3_key: str):
    """Delete a file from Google Drive. s3_key is the Drive file ID."""
    service = get_drive_service()
    try:
        service.files().delete(fileId=s3_key).execute()
        logger.info(f"Deleted file {s3_key} from Google Drive")
    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"File {s3_key} not found on Drive (already deleted?)")
        else:
            logger.error(f"Error deleting file {s3_key}: {e}")


def file_exists(s3_key: str) -> bool:
    """Check if a file exists in Google Drive. s3_key is the Drive file ID."""
    service = get_drive_service()
    try:
        service.files().get(fileId=s3_key, fields="id").execute()
        return True
    except HttpError:
        return False


def _make_public(file_id: str):
    """
    Grant 'anyone with the link' read access so the download URL works
    without authentication.
    """
    service = get_drive_service()
    try:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
        ).execute()
    except HttpError as e:
        logger.warning(f"Could not set public permission on {file_id}: {e}")
