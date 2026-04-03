import yt_dlp
import sys
url = "https://www.youtube.com/watch?v=9bZkp7q19f0"
ydl_opts = {
    'quiet': True,
    'skip_download': True,
    'extract_flat': True,
    'playlistend': 3,
    'source_address': '0.0.0.0',
    'extractor_args': {'youtube': {'client': ['android', 'ios']}},
}
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("SUCCESS:", info.get('title'))
except Exception as e:
    print("ERROR:", str(e))
