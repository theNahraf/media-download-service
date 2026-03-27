import os
import uuid
from flask import Flask, request, send_file, jsonify, render_template, after_this_request
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def download_video(url, mode):
    file_id = str(uuid.uuid4())

    if mode == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        formats = {
            "720": "bestvideo[height<=720]+bestaudio/best",
            "480": "bestvideo[height<=480]+bestaudio/best",
            "360": "bestvideo[height<=360]+bestaudio/best",
            "best": "bestvideo+bestaudio/best"
        }

        ydl_opts = {
            'format': formats.get(mode, "best"),
            'merge_output_format': 'mp4',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        if mode == "audio":
            filename = os.path.splitext(filename)[0] + ".mp3"
        else:
            filename = os.path.splitext(filename)[0] + ".mp4"

    return filename


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    mode = data.get("mode", "best")

    if not url:
        return jsonify({"error": "URL required"}), 400

    try:
        file_path = download_video(url, mode)

        @after_this_request
        def cleanup(response):
            try:
                os.remove(file_path)
            except:
                pass
            return response

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)