FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies required by yt-dlp (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start script: runs API + Worker + Beat in one container
# This is ideal for free-tier platforms (single service = single billing unit)
CMD ["bash", "-c", "celery -A worker.celery_app worker --concurrency=2 --loglevel=info & celery -A worker.celery_app beat --loglevel=info & uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
