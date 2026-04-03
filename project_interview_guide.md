# Media Download Service - Interview Guide & System Design

This document covers everything you need to know about your "Media Download Service" project. It includes High-Level Design (HLD), Low-Level Design (LLD), component breakdowns, data flows, and potential interview questions so you can explain exactly how the system works.

---

## 1. Project Overview
**What is this project?**
It is a highly scalable, asynchronous web service that allows users to submit URLs (like YouTube videos) to be processed, downloaded, and converted into specific media formats (audio or video) in the background. Users can track the progress of their downloads in real-time and eventually get a secure link to download the final file.

**Why is it built this way?** 
Downloading and converting media can take minutes (or longer for large playlists/videos). If you processed this in the main web request, the browser would time out, and the web server would crash under load. To solve this, the project uses an **Event-Driven, Asynchronous Architecture** via background jobs.

---

## 2. Tech Stack & Justifications
You should be prepared to explain *why* these tools were chosen.

*   **Backend Framework:** FastAPI (Python)
    *   *Why?* Extremely fast, native `async`/`await` support for high concurrency, built-in validation via Pydantic, and automatic Swagger documentation.
*   **Message Broker (Queue) & Cache:** Redis
    *   *Why?* Extremely fast in-memory data store. Used to queue jobs for Celery and temporarily cache real-time download progress (e.g., 45% downloaded) so the frontend can check it rapidly without overloading the main database.
*   **Background Worker:** Celery with `yt-dlp`
    *   *Why Celery?* The industry standard for distributed task processing in Python. It safely takes heavy tasks (downloading/converting) off the main API thread.
    *   *Why `yt-dlp`?* It's the most robust library for extracting media from hundreds of websites.
*   **Database:** PostgreSQL (with SQLAlchemy & Alembic)
    *   *Why?* Relational database ensures ACID compliance. Used as the permanent source of truth for "Jobs" (user requests), storing metadata, status, and S3 paths. Alembic handles database migrations.
*   **Object Storage:** MinIO / S3 (`boto3`)
    *   *Why?* Media files are large binaries. Databases are bad at storing files. We store files in S3/MinIO and save only the "reference path" to the file in PostgreSQL. This allows generation of secure, temporary signed URLs.
*   **Infrastructure:** Docker & Docker Compose
    *   *Why?* Ensures the app runs identically on your laptop (Local S3 via Minio, local Postgres, local Redis) as it does in production.

---

## 3. High-Level Design (HLD)

The system consists of three main isolated layers: The User Interface, the Public API, and the Private Worker layer.

### Architecture Data Flow
1. **Client Request:** User hits the frontend app and submits a URL (e.g., a YouTube link).
2. **API Layer (FastAPI):**
    *   The API validates the request.
    *   The API saves a new `Job` record in **PostgreSQL** with status `PENDING`.
    *   The API publishes a message to **Redis** telling Celery to start processing the job.
    *   The API returns a `job_id` to the client immediately (latency < 100ms).
3. **Client Polling:** The frontend uses the `job_id` to constantly poll the API for progress. The API reads the live percentage rapidly from **Redis cache**.
4. **Worker Layer (Celery):**
    *   A worker picks up the job from Redis.
    *   It updates Postgres status to `PROCESSING`.
    *   It runs `yt-dlp` to download the file into a temporary local folder. As it downloads, it constantly updates the current percentage directly in **Redis**.
5. **Storage Phase:**
    *   Once downloaded, Celery uploads the `.mp4` / `.mp3` file to **MinIO/S3**.
    *   Celery updates the **PostgreSQL** `Job` record to `COMPLETED` and saves the `s3_key` (file location) and metadata (duration, filesize).
6. **Delivery:**
    *   The polling client sees the `COMPLETED` status.
    *   The client asks the API for the file. The API generates an S3 **Pre-Signed URL** (a temporary, secure direct-download link) and gives it to the client.

---

## 4. Low-Level Design (LLD)

### Database Schema (SQLAlchemy - `api/models.py`)
The system revolves around the `jobs` table:
*   `id` (UUID): Primary key, sent to the client.
*   `url` (String): The target website URL.
*   `format` (Enum): 'video' or 'audio'.
*   `status` (Enum): PENDING, PROCESSING, UPLOADING, COMPLETED, FAILED, CANCELLED.
*   *Metadata properties:* `title`, `duration_seconds`, `file_size_bytes` (populated by the worker).
*   `s3_key`: Location in the cloud.
*   `client_ip` / `created_at`: For auditing/rate-limiting.

### Project Directory Structure
*   **`app.py` / `api/main.py`**: The FastAPI server. Mounts routers, initializes middleware (CORS, Rate Limiting), and manages startup events (checking DB and S3 connections).
*   **`api/routes/`**: The Controllers. E.g., `jobs.py` handles the POST `/jobs` and GET `/jobs/{id}` endpoints.
*   **`api/services/`**: Encapsulates external integrations. `storage_service.py` handles AWS S3 logic. `cache_service.py` handles Redis.
*   **`worker/tasks.py`**: The heavy lifting. Contains the `process_download(job_id)` function. Note how it uses `yt_dlp` hooks to intercept the download stream and push progress chunks into Redis!
*   **`alembic/`**: Contains Python scripts that represent versions of your database. If you add a new column to the `jobs` table, Alembic applies it to Postgres smoothly.
*   **`docker-compose.yml`**: Defines seven containers that talk to each other over a virtual network: `api`, `worker`, `beat` (for scheduled cleanups), `postgres`, `redis`, `minio` (local S3), and `flower` (a UI dashboard for monitoring Celery queues).

---

## 5. Key Technical Implementations to Mention in Interviews

If asked "What were the challenging parts of this project?", mention these features:

1. **Decoupling heavy compute from web requests:** By using Celery, the API node only handles JSON routing and DB reads/writes. If 1,000 people request downloads, the API handles it easily, and the Celery workers just process them from the queue at their own pace without crashing.
2. **Real-time Progress Tracking:** Postgres is too slow and heavy to handle a worker writing to it every single second as bytes download. We specifically used **Redis** to store the live progress percentage using the Job ID as the key.
3. **File System Abstraction (S3):** The workers are stateless. They download files to a temporary folder (`/tmp`), upload them to S3, and delete the local file. This allows scaling horizontally (adding 10 worker servers) without worrying about "which server holds which file".
4. **Resiliency & Retries:** In `worker/tasks.py`, `acks_late=True` and `reject_on_worker_lost=True` are configured on the Celery task. If a worker container crashes at 90% download, the job is put *back* into the queue for another worker to pick up safely instead of disappearing. It also includes explicit retries (`max_retries=3`) built-in.
5. **Security (Presigned URLs):** S3 bucket objects are completely private. Users never interact directly with S3. The API generates a time-bound mathematical cryptographic signature (Presigned URL) that allows the user specific access to just their file for a few minutes.

---

## 6. Common Interview Questions & Answers

**Q: Why didn't you just use Python `threading` or `asyncio` instead of Celery and Redis?**
*Answer:* `asyncio` is great for waiting on I/O (like waiting for a database response). However, media chunking and extraction take heavy CPU cycles and unpredictable memory, which block the main event loop if done linearly. Additionally, using Celery + Redis allows for distributed scaling. I can host the web API on one machine, and put 5 celery worker containers on different heavy-compute machines. You can't distribute local threads across machines.

**Q: What happens if a user submits a playlist with 100 videos?**
*Answer:* The worker task has logic to handle playlists smoothly. I implemented a hook inside the `yt-dlp` initialization in `worker/tasks.py` that checks `playlist_index` and `n_entries`. It tracks bytes downloaded across *all* files to provide an accurate overall progress percentage to the client via Redis, treating it as a single job state.

**Q: How do you prevent people from spamming the service and racking up massive AWS S3/Compute bills?**
*Answer:* We have `RateLimitMiddleware` sitting in the FastAPI pipeline. We also track `client_ip` in the database. Furthermore, Celery sets a maximum concurrency limit, so we never process more than `X` files at a time. I also implemented `beat.py` / `cleanup.py` tasks which are cron jobs that routinely scan the database for old successfully uploaded files and delete them from the database and S3 to keep storage costs zero-sum.

**Q: How do you handle database migrations when adding new features?**
*Answer:* I use Alembic. I define my models in SQLAlchemy, and then run `alembic revision --autogenerate`. This creates a repeatable script that alters the Postgres schema, which is run automatically on container startup or via CI/CD before deployments.
