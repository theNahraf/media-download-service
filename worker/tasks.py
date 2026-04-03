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
from worker.redis_sync import update_progress, update_playlist_progress, clear_playlist_progress
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

    # ── Sanitize YouTube Mix/Radio URLs ──
    # URLs like ?v=xxx&list=RDxxx&start_radio=1 are YouTube Mix playlists.
    # Strip the playlist params so yt-dlp downloads only the single video.
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed_url = urlparse(url)
    if parsed_url.hostname and "youtube" in parsed_url.hostname:
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)
        video_id = query_params.get("v")
        if video_id:
            # If there's a video ID, strip everything else — get clean single-video URL
            clean_query = urlencode({"v": video_id[0]})
            url = urlunparse(parsed_url._replace(query=clean_query))
            logger.info(f"Sanitized YouTube URL to single video: {url}")

    update_job_status(job_id, JobStatus.PROCESSING)
    update_progress(job_id, 0)
    
    # Create isolated temp dir for this job
    job_temp_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_temp_dir, exist_ok=True)
    
    try:
        # Playlist tracking state (updated inside hook)
        playlist_state = {"current": 0, "total": 0, "current_title": "", "bytes_downloaded": 0}

        def my_hook(d):
            if d['status'] == 'downloading':
                try:
                    info_dict = d.get('info_dict', {})

                    # Track playlist video changes by watching playlist_index
                    idx = info_dict.get('playlist_index') or info_dict.get('n_entries')
                    if idx and playlist_state["total"] > 1:
                        # Detect when we move to a new video
                        if idx != playlist_state["current"]:
                            playlist_state["current"] = idx
                            playlist_state["current_title"] = info_dict.get('title', '...')

                    # Per-video download % (0-100)
                    p_str = d.get('_percent_str', '0%') \
                        .replace('\x1b[0;94m', '').replace('\x1b[0m', '').replace('%', '').strip()
                    per_video_pct = max(0, min(100, int(float(p_str or '0'))))

                    # Bytes stats
                    downloaded_bytes = d.get('downloaded_bytes') or 0
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    playlist_state["bytes_downloaded"] = downloaded_bytes
                    if total_bytes:
                        playlist_state["bytes_total"] = total_bytes

                    # For playlists: overall % = completed videos + fraction of current
                    if playlist_state["total"] > 1:
                        curr = playlist_state["current"] or 1
                        total = playlist_state["total"]
                        overall_pct = int(((curr - 1) / total) * 100 + (per_video_pct / total))
                        update_progress(job_id, overall_pct)
                        update_playlist_progress(
                            job_id, curr, total,
                            playlist_state["current_title"],
                            downloaded_bytes,
                            playlist_state.get("bytes_total", 0)
                        )
                    else:
                        update_progress(job_id, per_video_pct)
                        # Store bytes for single video
                        from worker.redis_sync import redis_client
                        redis_client.setex(f"job:{job_id}:bytes", 600,
                            f"{downloaded_bytes},{total_bytes}")
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
                'no_warnings': True,
                'playlistend': 50,
                'source_address': '0.0.0.0', # Force IPv4 to bypass cloud network blocks
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
                'no_warnings': True,
                'playlistend': 50,
                'source_address': '0.0.0.0', # Force IPv4 to bypass cloud network blocks
            }

        # Step 1: Extract info and download
        logger.info(f"Downloading {url} to {job_temp_dir}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract info to update DB
            info = ydl.extract_info(url, download=False)
            
            # Detect if this is a playlist and prime state BEFORE downloading
            entries = info.get('entries') if info else None
            if entries:
                entry_list = list(entries)
                playlist_state["total"] = min(len(entry_list), 50)
                playlist_state["current"] = 1
                # Try to get title of first entry
                first = entry_list[0] if entry_list else {}
                playlist_state["current_title"] = first.get('title', info.get('title', 'Playlist'))
            
            update_job_metadata(job_id, info)
            
            # Then download
            ydl.extract_info(url, download=True)
            
            # Check what was actually downloaded
            downloaded_files = [f for f in os.listdir(job_temp_dir) if os.path.isfile(os.path.join(job_temp_dir, f))]
            
            if not downloaded_files:
                raise Exception("No files were downloaded.")
                
            if len(downloaded_files) == 1:
                # Single file download
                base_name = downloaded_files[0]
                filename = os.path.join(job_temp_dir, base_name)
                extension = os.path.splitext(base_name)[1].lower()
                
                # Determine content type based on extension
                if extension in ['.jpg', '.jpeg', '.png', '.webp']:
                    content_type = f"image/{extension[1:]}"
                elif extension in ['.mp3', '.m4a', '.wav']:
                    content_type = "audio/mpeg"
                else:
                    content_type = "video/mp4"
                
                file_size = os.path.getsize(filename)
                s3_key = f"downloads/{job_id}{extension}"
                upload_target = filename
            else:
                # Multiple files (playlist or carousel), zip them
                title_clean = str(info.get('title', 'playlist')).replace('/', '_')
                base_name = f"{title_clean}.zip"
                
                zip_filename = os.path.join(DOWNLOAD_DIR, f"{job_id}.zip")
                shutil.make_archive(zip_filename[:-4], 'zip', job_temp_dir)
                
                filename = zip_filename
                extension = ".zip"
                content_type = "application/zip"
                file_size = os.path.getsize(filename)
                s3_key = f"downloads/{job_id}.zip"
                upload_target = filename

            # Step 2: Upload to Storage
            logger.info(f"Uploading {base_name} to Storage")
            update_job_status(job_id, JobStatus.UPLOADING, file_size_bytes=file_size, original_filename=base_name)
            
            drive_file_id = upload_file(
                upload_target, 
                s3_key, 
                content_type=content_type, 
                original_filename=base_name
            )
            
            # Cleanup zip if we created it
            if len(downloaded_files) > 1 and os.path.exists(upload_target):
                os.remove(upload_target)
            
            # Step 3: Cleanup and mark complete
            # Use the Google Drive file ID (not the old S3 path) for download URL generation
            update_job_status(
                job_id,
                JobStatus.COMPLETED,
                s3_key=drive_file_id,
                completed_at=datetime.now(timezone.utc)
            )
            update_progress(job_id, 100)
            clear_playlist_progress(job_id)
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
