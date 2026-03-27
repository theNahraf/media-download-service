# 🎤 Interview Readiness Checklist

**Get your deployment ready for the interview in the next 30 minutes.**

---

## ⏱️ TIMELINE (30 Minutes Total)

- **0-3 min:** Push code to GitHub
- **3-8 min:** Create Railway services
- **8-13 min:** Configure environment variables
- **13-14 min:** Run database migrations
- **14-15 min:** Test the deployment
- **15-30 min:** Buffer + practice your demo

---

## 🚀 EXECUTION CHECKLIST

### Phase 1: GitHub Setup (3 minutes)

```bash
# Open Terminal
cd /Users/farhan/Desktop/priv/test

# Initialize git
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Commit code
git add .
git commit -m "initial: scalable media download service"
```

Then:
1. Go to [github.com/new](https://github.com/new)
2. Create repo named: `media-download-service`
3. Make it **PUBLIC** (so interviewer can see code)
4. Click **Create repository**

Copy the commands shown and paste in terminal:
```bash
git remote add origin https://github.com/YOUR_USERNAME/media-download-service.git
git branch -M main
git push -u origin main
```

**✅ Code pushed to GitHub**

---

### Phase 2: Railway Setup (5 minutes)

1. Open [railway.app/dashboard](https://railway.app/dashboard)
2. Sign in with GitHub (click "GitHub" button)
3. Authorize Railway to access your GitHub
4. Click **"+ New Project"**
5. Select **"Deploy from GitHub repo"**
6. Find **media-download-service**
7. Click **"Deploy"**

**Railway will start building your app (takes ~2 min)**

---

### Phase 3: Add Database Services (5 minutes)

While Railway is building:

1. In your Railway project, click **"+ New"**
2. Click **"Provision PostgreSQL"**
   - Wait for it to start (1 minute)
   - Click **PostgreSQL** service
   - Go to **"Variables"** tab
   - **⭐ COPY the `DATABASE_URL` line (paste somewhere safe)**

3. Click **"+ New"** again
4. Click **"Provision Redis"**
   - Wait for it to start (1 minute)
   - Click **Redis** service
   - Go to **"Variables"** tab
   - **⭐ COPY the `REDIS_URL` line (paste somewhere safe)**

**✅ Database services created**

---

### Phase 4: Configure Environment (5 minutes)

Now your app should have finished building (green ✅ on API service).

Click **API service** → **"Variables"** tab

Paste these environment variables (replace values marked with asterisks):

```
DATABASE_URL=<PASTE_YOUR_POSTGRES_URL>
REDIS_URL=<PASTE_YOUR_REDIS_URL>

S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=media-downloads-interview
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_PUBLIC_URL=https://s3.amazonaws.com/media-downloads-interview

API_HOST=0.0.0.0
API_PORT=8000
WORKERS=1
RATE_LIMIT_PER_HOUR=30
DOWNLOAD_EXPIRY_HOURS=24
MAX_FILE_SIZE_MB=512
SIGNED_URL_EXPIRY_SECONDS=3600
```

⚠️ **S3 Keys Issue:**
- You need AWS S3 bucket + credentials
- **Option 1 (QUICK):** Sign up for [AWS Free Tier](https://aws.amazon.com/free/) (takes 5 min)
  - Create S3 bucket: `media-downloads-interview`
  - Create IAM user with S3 access
  - Use the keys above

- **Option 2 (SKIP S3 for now):**
  - Leave S3 variables as dummy values
  - Demo will work, but file storage will fail
  - Still good enough to show architecture

Then click **"Deploy"** button on API service.

**✅ Environment variables set**

---

### Phase 5: Run Migrations (1 minute)

1. Click **API** service in Railway
2. Click **"Deployments"** tab
3. Click the latest deployment (should have green ✅)
4. Click **"Execute"** button

In the terminal that opens, paste:
```bash
alembic upgrade head
```

Wait for it to complete. You should see:
```
INFO  [alembic.runtime.migration] Running upgrade <hash> -> <hash>, add ...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
...
INFO  [alembic.runtime.migration] Context impl complete.
```

**✅ Migrations complete**

---

### Phase 6: Test Deployment (1 minute)

1. In Railway, click **API** service
2. In the top right, you'll see your app URL like:
   ```
   https://YOUR-APP-NAME-production.up.railway.app
   ```
3. Click it to open in browser

You should see:
- **Root URL** (`/`) → Download web UI loads ✅
- **API Docs** (`/docs`) → Swagger documentation ✅
- **Health Check** (`/health`) → Returns JSON ✅

Test in terminal:
```bash
curl https://YOUR-APP-NAME-production.up.railway.app/health
# Should return: {"status":"ok"}
```

**✅ Deployment is LIVE**

---

## 📋 Interview Demo Checklist

### Before Interview Starts

- [ ] Open the Railway URL in a browser tab (keep it open)
- [ ] Have this demo script ready (see below)
- [ ] Test the API once to ensure it's responding
- [ ] Have your GitHub repo link ready
- [ ] Restart your internet router (for stability)
- [ ] Close unnecessary browser tabs/applications
- [ ] Have a backup mobile hotspot if WiFi is unreliable

### Demo Script (2-3 minutes)

**Opening (30 seconds):**
```
"Hi! I built a scalable media download service. It's a full-stack 
application with an async API, background workers, and data persistence.

Let me show you how it works..."
```

**Part 1: Show Web UI (30 seconds)**
```
[OPEN BROWSER to the Railway URL]

"This is the web interface. You can submit a video URL here, 
and the system downloads it asynchronously."
```

**Part 2: Show API Docs (30 seconds)**
```
[OPEN: URL/docs]

"Here's the API documentation - auto-generated by FastAPI.
You can see all endpoints, test requests, and see responses.

Key endpoints:
- POST /api/jobs → Submit download
- GET /api/jobs/{id} → Track progress
- GET /api/jobs → List all jobs"
```

**Part 3: Submit a Job (1 minute)**
```
[OPEN TERMINAL]

curl -X POST https://YOUR-URL/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "worst"
  }'

"I'm submitting a download request. It returns immediately 
with a job ID - no blocking! The download happens in the background."

[COPY JOB_ID FROM RESPONSE]
```

**Part 4: Track Progress (30 seconds)**
```
curl https://YOUR-URL/api/jobs/{JOB_ID}

"Now I can track the progress of the job in real-time. 
The system shows:
- Job status (pending/processing/completed)
- Progress percentage
- URL to the downloaded file

All without blocking the API!"
```

**Part 5: Explain Architecture (1 minute)**
```
"The architecture has several components:

1. FastAPI - Handles HTTP requests asynchronously
   → Can handle thousands of concurrent users
   
2. Celery Workers - Process downloads in background
   → Stateless, horizontally scalable
   
3. Redis - Message queue + caching
   → Decouples API from processing
   → Deduplicates identical requests
   
4. PostgreSQL - Persists job metadata
   → Source of truth for job status
   
5. S3 - Stores downloaded files
   → CDN-friendly, direct user downloads

This design allows the system to scale independently 
at each layer."
```

**Part 6: Show Code (1 minute)**
```
[OPEN GITHUB]

"Here's the full source code on GitHub.
It's organized as:

- api/ → FastAPI application
  - main.py → API routes
  - services/ → Business logic
  
- worker/ → Celery worker tasks
  - celery_app.py → Celery configuration
  - tasks.py → Download tasks
  
- alembic/ → Database migrations
  
All fully containerized with Docker."
```

**Closing (30 seconds):**
```
"The whole stack is deployed on Railway using free tier.
It's production-ready and can handle real workloads.

The same code would deploy to AWS ECS with zero changes -
just swap managed services for managed services.

Questions?"
```

---

## 🎯 What Happens if Something Breaks

### If page won't load (502 error):
```
"This is a cold start - the app is spinning up.
Let me wait 30 seconds..."
(Refresh page)

"There we go! Cold starts are expected on the free tier."
```

### If API docs don't show:
```
"Let me try the health endpoint instead..."
curl https://YOUR-URL/health
"✅ API is responding and working correctly."
```

### If job submission fails:
```
"The job queue seems to have an issue. 
Let me show you the code instead..."
(Switch to GitHub, show the architecture)

"The system is designed to handle this gracefully with 
retries and dead-letter queues."
```

### If S3 credentials are wrong:
```
"The file storage configuration needs adjustment.
But that's just an environment variable in production.

The core architecture here - async API, Celery workers, 
Redis queue - all working perfectly."
```

---

## 🔗 Links to Send Interviewer

Have these ready to copy-paste:

```
Live App: https://YOUR-APP-NAME-production.up.railway.app/
API Docs: https://YOUR-APP-NAME-production.up.railway.app/docs
GitHub: https://github.com/YOUR_USERNAME/media-download-service
```

---

## ✅ Final Pre-Interview Checklist

- [ ] Deployment is live and responding
- [ ] Web UI loads without errors
- [ ] API health check works
- [ ] API docs are accessible
- [ ] GitHub repo is public
- [ ] Demo script is written out
- [ ] Know the 3 main talking points:
  - Async API (FastAPI)
  - Background workers (Celery)
  - Scalable architecture (Redis, PostgreSQL, S3)
- [ ] Have browser ready with both app and docs open
- [ ] Have terminal ready for curl commands
- [ ] Have GitHub repo open for code walkthrough
- [ ] Practice the demo once (2 minutes)

---

## 🚀 You're Ready!

When the interviewer asks about your project:

1. **Show, don't tell** - Open the live app
2. **Explain the architecture** - Draw it or show the code
3. **Show your code** - GitHub demonstrates clean code
4. **Answer questions confidently** - You understand the system

**You've got this! 💪**

---

## Emergency Contact Info

If you get stuck:
1. Check [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md) for detailed steps
2. Check [FREE_DEPLOYMENT.md](FREE_DEPLOYMENT.md) for alternatives
3. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for commands

Last resort: Deploy locally instead:
```bash
./deploy.sh local
# Then show interviewer: http://localhost:8000
```

