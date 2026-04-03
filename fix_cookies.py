import os
def configure_cookies(ydl_opts):
    cookie_str = os.getenv("YOUTUBE_COOKIES", "")
    if cookie_str:
        with open("/tmp/yt_cookies.txt", "w") as f:
            f.write(cookie_str.replace("\\n", "\n"))
        ydl_opts["cookiefile"] = "/tmp/yt_cookies.txt"
    return ydl_opts
