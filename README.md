
# Media Download Service

A web-based media downloader that allows users to download videos or extract audio from YouTube links with selectable quality options. Built using Flask and yt-dlp.

---

## 🚀 Features

- Download videos in multiple qualities (360p, 480p, 720p, Best)
- Extract audio as MP3
- Simple web interface for quick usage
- Preserves original YouTube video title as filename
- Clean API-driven backend

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Media Processing:** yt-dlp
- **Frontend:** HTML, CSS, JavaScript
- **Other:** FFmpeg (for merging audio/video & audio extraction)

---

## 📁 Project Structure

```

project/
├── app.py
├── templates/
│   └── index.html
├── downloads/
├── requirements.txt

````

---

## ⚙️ Setup & Run Locally

### 1. Clone repository

```bash
git clone https://github.com/<your-username>/media-download-service.git
cd media-download-service
````

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

```bash
brew install ffmpeg   # Mac
# or
sudo apt install ffmpeg   # Linux
```

### 5. Run the server

```bash
python app.py
```

### 6. Open in browser

```

http://127.0.0.1:5000

```

---

## 📡 API Endpoints

### POST `/download`

Download video or audio.

#### Request Body

```json
{
  "url": "https://youtube.com/...",
  "mode": "best | 720 | 480 | 360 | audio"
}
```

#### Response

* Returns file download directly

---

## ⚠️ Limitations

* Downloads are synchronous (request blocks until completion)
* Files are stored temporarily on local disk
* Not optimized for high concurrency or large-scale usage

---

## 💡 Future Improvements

* Asynchronous processing using queue (Redis + workers)
* Progress tracking (WebSockets / SSE)
* Cloud storage integration (AWS S3)
* Support for multiple platforms beyond YouTube
* Authentication & rate limiting

---

## 📌 Notes

* Requires FFmpeg for proper audio/video merging
* Uses yt-dlp under the hood for media extraction

---

## 🧠 Learning Outcomes

* Built an end-to-end media processing pipeline
* Integrated third-party CLI tools into a web backend
* Designed API-driven architecture for file handling
* Understood limitations of synchronous processing

---
