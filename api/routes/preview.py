"""
Preview route — fast metadata extraction without downloading.
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import yt_dlp

from api.schemas import ALLOWED_DOMAINS

router = APIRouter(prefix="/api/v1/preview", tags=["Preview"])


def _extract_info_sync(url: str) -> dict:
    """Run yt-dlp info extraction synchronously (called in thread pool)."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': True,   # Fast — don't recurse into each video for playlists
        'playlistend': 3,        # Only look at first 3 entries for speed
        'source_address': '0.0.0.0', # Force IPv4 to bypass cloud network blocks
        'extractor_args': {'youtube': {'client': ['android', 'ios']}}, # Bypass HTML bot check
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info or {}


def _extract_single_video_size(url: str) -> int:
    """Get approximate file size of the best format for a single video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'source_address': '0.0.0.0', # Force IPv4 to bypass cloud network blocks
        'extractor_args': {'youtube': {'client': ['android', 'ios']}}, # Bypass HTML bot check
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return 0
            # Sum up filesize from requested_formats (video + audio) when merged
            total = 0
            for fmt in (info.get('requested_formats') or [info]):
                total += fmt.get('filesize') or fmt.get('filesize_approx') or 0
            return total
    except Exception:
        return 0


@router.get("")
async def preview_url(url: str = Query(..., description="Media URL to preview")):
    """
    Fetch video/playlist metadata for display before download.
    Runs yt-dlp extract_info in a thread so the event loop isn't blocked.
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    # Domain allowlist check
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_DOMAINS:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {hostname}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")

    # Sanitize YouTube Mix URLs
    if "youtube" in hostname:
        q = parse_qs(parsed.query, keep_blank_values=True)
        vid = q.get("v")
        if vid:
            url = urlunparse(parsed._replace(query=urlencode({"v": vid[0]})))

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract_info_sync, url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch info: {str(e)[:200]}")

    # Detect playlist vs single video
    entries = info.get("entries")
    if entries:
        entry_list = list(entries)
        first = entry_list[0] if entry_list else {}
        thumbnail = first.get("thumbnail") or info.get("thumbnail") or ""
        return {
            "type": "playlist",
            "title": info.get("title", "Playlist"),
            "thumbnail": thumbnail,
            "video_count": info.get("playlist_count") or len(entry_list),
            "channel": info.get("uploader") or info.get("channel", ""),
            "duration_seconds": None,
            "filesize_bytes": None,  # Too expensive to sum entire playlist
        }
    else:
        # Fetch file size concurrently with a deeper call
        filesize = await loop.run_in_executor(None, _extract_single_video_size, url)
        return {
            "type": "video",
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration_seconds": info.get("duration"),
            "channel": info.get("uploader") or info.get("channel", ""),
            "video_count": None,
            "filesize_bytes": filesize if filesize else None,
        }
