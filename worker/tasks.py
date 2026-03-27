"""
Celery tasks for background processing (yt-dlp and S3 upload).
"""
import os
import shutil
import tempfile
import yt_dlp
from datetime import datetime, timezone
from celery.utils.log import get_task_logger

from worker.celery_app import celery_app
from worker.db_sync import SessionLocal, update_job_status, update_job_metadata, increment_retry_count, mark_job_failed
from worker.redis_sync import update_progress
from api.models import Job, JobStatus
from api.services.storage_service import upload_file

logger = get_task_logger(__name__)

# Temporary directory for processing
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/mediadownloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60, # 1 minute base delay
    acks_late=True, # Important for reliability
    reject_on_worker_lost=True
)
def process_download(self, job_id: str):
    """
    Background job to download media and upload to storage.
    """
    logger.info(f"Starting job {job_id}")
    
    with SessionLocal() as db:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database.")
            return

        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} cancelled.")
            return
            
        url = job.url
        mode = job.format.value
        quality = job.quality

    update_job_status(job_id, JobStatus.PROCESSING)
    update_progress(job_id, 0)
    
    # Create isolated temp dir for this job
    job_temp_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_temp_dir, exist_ok=True)
    
    try:
        def my_hook(d):
            if d['status'] == 'downloading':
                try:
                    # Remove ANSI escape codes and % sign
                    p_str = d.get('_percent_str', '0%') \
                        .replace('\x1b[0;94m', '').replace('\x1b[0m', '').replace('%', '').strip()
                    percent = int(float(p_str))
                    update_progress(job_id, percent)
                except Exception:
                    pass

        # Configure yt-dlp based on format
        if mode == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{job_temp_dir}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'progress_hooks': [my_hook],
                'quiet': True,
                'no_warnings': True
            }
        else:
            formats = {
                "1080p": "bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best",
                "720p": "bestvideo[height<=720]+bestaudio/bestvideo+bestaudio/best",
                "480p": "bestvideo[height<=480]+bestaudio/bestvideo+bestaudio/best",
                "360p": "bestvideo[height<=360]+bestaudio/bestvideo+bestaudio/best",
                "best": "bestvideo+bestaudio/best"
            }

            ydl_opts = {
                'format': formats.get(quality, "best"),
                'merge_output_format': 'mp4',
                'outtmpl': f'{job_temp_dir}/%(title)s.%(ext)s',
                'progress_hooks': [my_hook],
                'quiet': True,
                'no_warnings': True
            }

        # Step 1: Extract info and download
        logger.info(f"Downloading {url} to {job_temp_dir}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract info to update DB
            info = ydl.extract_info(url, download=False)
            update_job_metadata(job_id, info)
            
            # Then download
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if mode == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"
            else:
                filename = os.path.splitext(filename)[0] + ".mp4"
                
            base_name = os.path.basename(filename)
            file_size = os.path.getsize(filename)
            
            # Step 2: Upload to Storage
            logger.info(f"Uploading {filename} to Storage")
            update_job_status(job_id, JobStatus.UPLOADING, file_size_bytes=file_size, original_filename=base_name)
            
            extension = os.path.splitext(base_name)[1]
            s3_key = f"downloads/{job_id}{extension}"
            
            content_type = "audio/mpeg" if mode == "audio" else "video/mp4"
            
            upload_file(
                filename, 
                s3_key, 
                content_type=content_type, 
                original_filename=base_name
            )
            
            # Step 3: Cleanup and mark complete
            update_job_status(
                job_id,
                JobStatus.COMPLETED,
                s3_key=s3_key,
                completed_at=datetime.now(timezone.utc)
            )
            update_progress(job_id, 100)
            logger.info(f"Job {job_id} completed successfully")

    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"Download error for {job_id}: {e}")
        # Could be transient rate limiting or permanent error
        increment_retry_count(job_id)
        raise self.retry(exc=e)
        
    except Exception as e:
        logger.error(f"Unexpected error for {job_id}: {e}")
        increment_retry_count(job_id)
        # Check retry limit manually if we wanted, but Celery handles MaxRetriesExceededError
        try:
            raise self.retry(exc=e)
        except Exception as retry_exc:
            # We hit max retries or it's non-retryable
            mark_job_failed(job_id, str(e))
            raise e

    finally:
        # Guarantee cleanup of local file
        if os.path.exists(job_temp_dir):
            shutil.rmtree(job_temp_dir, ignore_errors=True)
