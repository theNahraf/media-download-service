# 🆓 Free Deployment Guide (Railway / Render)

Deploy your Media Download Service **completely free** for interviews with Railway or Render.

---

## Quick Comparison

| Platform | Free Tier | Best For | Setup Time |
|----------|-----------|----------|-----------|
| **Railway** | $5/month credit (very generous) | Docker projects | 5 min ⚡ |
| **Render** | Free PostgreSQL + 0.5GB RAM | Full stack | 10 min |
| **Fly.io** | ~3 shared-cpu 1GB VMs free | Production-ready | 15 min |

**Recommendation:** **Railway** for interviews (fastest, most straightforward)

---

## 🚀 Deploy to Railway (Recommended - 5 Minutes)

### Step 1: Prepare Your Repository

```bash
# 1a. Initialize git (if not already done)
cd /Users/farhan/Desktop/priv/test
git init
git add .
git commit -m "Initial commit: Media Download Service"

# 1b. Push to GitHub
# Create a new repo on GitHub (https://github.com/new)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/media-download-service.git
git branch -M main
git push -u origin main
```

### Step 2: Create Railway Account

1. Go to https://railway.app
2. Click "Start New Project"
3. Sign up with GitHub (easiest)
4. Authorize railway-app to access your GitHub

### Step 3: Create Services

#### A. Database (PostgreSQL)
```
1. Click "+ New"
2. Select "PostgreSQL"
3. Railway creates postgres:5432 automatically
4. Copy the DATABASE_URL from the Variables tab
   Format: postgresql://user:password@host:port/dbname
```

#### B. Redis (Cache)
```
1. Click "+ New"
2. Select "Redis"
3. Railway creates redis:6379 automatically
4. Copy the REDIS_URL from the Variables tab
   Format: redis://default:password@host:port
```

#### C. Deploy Your App
```
1. Click "+ New" → Deploy from GitHub repo
2. Select: YOUR_USERNAME/media-download-service
3. Select branch: main
4. Railway auto-detects it needs docker-compose
```

### Step 4: Configure Environment Variables

In Railway dashboard, click your app → "Variables" tab:

```env
# Database (auto-generated, copy from Railway)
DATABASE_URL=postgresql://...

# Redis (auto-generated, copy from Railway)
REDIS_URL=redis://...

# S3 / MinIO (Use Railway's built-in file storage OR free S3 alternative)
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=media-downloads-interview
S3_REGION=us-east-1
S3_ACCESS_KEY=YOUR_AWS_KEY
S3_SECRET_KEY=YOUR_AWS_SECRET
S3_PUBLIC_URL=https://s3.amazonaws.com/media-downloads-interview

# API
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=2

# Other settings
RATE_LIMIT_PER_HOUR=30
DOWNLOAD_EXPIRY_HOURS=24
MAX_FILE_SIZE_MB=512
```

**For S3 (Free Option):** Use **AWS Free Tier** S3 bucket:
- Sign up for [AWS Free Tier](https://aws.amazon.com/free/)
- Create S3 bucket
- Create IAM user with S3 permissions
- Use keys in environment variables

### Step 5: Update docker-compose.yml for Railway

Create `docker-compose.railway.yml` (or update existing):

```yaml
version: '3.8'

services:
  api:
    build: 
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      S3_ENDPOINT_URL: ${S3_ENDPOINT_URL}
      S3_BUCKET_NAME: ${S3_BUCKET_NAME}
      S3_ACCESS_KEY: ${S3_ACCESS_KEY}
      S3_SECRET_KEY: ${S3_SECRET_KEY}
      S3_PUBLIC_URL: ${S3_PUBLIC_URL}
      API_HOST: 0.0.0.0
      API_PORT: 8000

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      S3_ENDPOINT_URL: ${S3_ENDPOINT_URL}
      S3_BUCKET_NAME: ${S3_BUCKET_NAME}
      S3_ACCESS_KEY: ${S3_ACCESS_KEY}
      S3_SECRET_KEY: ${S3_SECRET_KEY}
      CELERY_BROKER_URL: ${REDIS_URL}
      CELERY_RESULT_BACKEND: ${REDIS_URL}
```

### Step 6: Deploy

```bash
# Push to GitHub (Railway auto-deploys on push)
git add .
git commit -m "Add Railway deployment config"
git push origin main

# Watch in Railway dashboard for deployment status
# Should be live in 2-3 minutes
```

### Step 7: Run Migrations

In Railway dashboard:
1. Click your app service
2. Go to "Deployments" tab
3. Click the latest deployment
4. Open the "Execute" tab
5. Run:
```bash
alembic upgrade head
```

### Step 8: Verify Deployment

```bash
# Get your app URL from Railway dashboard
# Format: https://YOUR_APP_NAME.railway.app

curl https://YOUR_APP_NAME.railway.app/health
# Expected: 200 OK
```

Your app is now live! 🎉

---

## 🆓 Deploy to Render (Free Alternative)

If Railway doesn't work, use Render:

### Step 1: Create Services

1. Go to https://render.com
2. Create account (GitHub sign-up)
3. Create new PostgreSQL (free)
4. Create new Redis (free tier available as add-on)

### Step 2: Deploy App

```bash
# Add render.yaml to your repo
cat > render.yaml << 'EOF'
services:
  - type: web
    name: media-download-api
    runtime: docker
    plan: free
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        value: postgresql://...
      - key: REDIS_URL
        value: redis://...
EOF

git add render.yaml
git commit -m "Add Render deployment config"
git push origin main
```

3. In Render dashboard:
   - New → Web Service
   - Connect GitHub repo
   - Render deploys automatically

---

## 🎬 Pre-Interview Checklist

### Before Your Interview
- [ ] Deployment is live (check URL in browser)
- [ ] API health check works: `/health` endpoint returns 200
- [ ] Web UI loads: visit root URL
- [ ] API docs accessible: `/docs` shows Swagger UI
- [ ] Test job submission works
- [ ] Worker processes job (check Flower if available)
- [ ] File uploads to S3 successfully
- [ ] Download link works

### Quick Interview Demo Script
```bash
# 1. Show API is running
curl https://YOUR_APP.railway.app/health
# Show: {"status": "ok"}

# 2. Show API docs
# Open: https://YOUR_APP.railway.app/docs
# Show interactive Swagger UI

# 3. Submit a test job
curl -X POST https://YOUR_APP.railway.app/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best"
  }'
# Show: Job ID and status

# 4. Track job progress
curl https://YOUR_APP.railway.app/api/jobs/{JOB_ID}
# Show: Progress percentage updating in real-time

# 5. Show web UI
# Open: https://YOUR_APP.railway.app
# Show: Download interface working
```

---

## ⚠️ Important Limits (Stay Within Free Tier)

### Railway Free Tier
- **$5 credit/month** = ~500 hours of small container
- **Storage:** 10GB
- **Build minutes:** Unlimited
- **Bandwidth:** 100GB/month outbound

**Recommendation:** Limit to 1 API + 1 Worker instance

### Render Free Tier
- **Compute:** Shared CPU, 0.5GB RAM
- **Database:** 1 free PostgreSQL database
- **Cold starts:** App spins down after 15 min inactivity
- **Storage:** 100GB

**Limitation:** Slow response after cold start (≤5s)

---

## 🔧 Cost Optimization Tips

1. **Use 1 Worker Instance** (not 4)
   - Edit `.env`: `WORKERS=1`

2. **Reduce Database Connections**
   - Edit `api/config.py`: Limit pool size to 5

3. **Compress Video Quality in Demo**
   - Show downloading at "worst" quality first for quick demo
   - "best" quality takes longer

4. **Enable Response Caching**
   - Cache `/health` and `/docs` responses

5. **Use Smaller Test Videos**
   - Pre-download a small video for demo
   - Have it ready in S3 before interview

---

## 🚨 Troubleshooting

### Deployment Fails
```bash
# Check logs in Railway/Render dashboard
# Common issues:

# 1. Missing environment variable
# Solution: Add in dashboard Variables tab

# 2. Database not ready
# Solution: Wait 2 min after creating DB, then redeploy

# 3. Docker build fails
# Solution: Check Dockerfile syntax
docker build -f Dockerfile.api .
```

### App Crashes on Startup
```bash
# Check logs in Railway dashboard
# Likely causes:

# 1. Migration failed
# Solution: Run manually via dashboard Execute tab
alembic upgrade head

# 2. Can't connect to database
# Solution: Verify DATABASE_URL is correct

# 3. Redis connection failed
# Solution: Verify REDIS_URL is correct
```

### Slow Response / Cold Start
- **On Render:** Expected (free tier has cold starts)
- **Solution:** Show this is a known limitation of free tier

### Worker Not Processing Jobs
```bash
# Check Redis connectivity
# Solution: Verify REDIS_URL variable is set

# Check worker logs in dashboard
# Solution: Restart worker service
```

---

## 📊 Minimal Config for Interview

Here's the **bare minimum** `.env` for a working demo:

```env
# Database (from Railway/Render)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis (from Railway/Render)
REDIS_URL=redis://default:pass@host:6379

# S3 (use AWS Free Tier bucket)
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=media-downloads-interview-demo
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_PUBLIC_URL=https://s3.amazonaws.com/media-downloads-interview-demo

# API
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=1
```

---

## 🎯 Expected Interview Questions & Answers

**Q: How is this deployed?**
> Railway.app - $5/month free tier. PostgreSQL and Redis managed services. API and Worker containerized via Docker.

**Q: How does it handle scale?**
> Horizontally scalable via Celery workers. Redis queue decouples API from processing. Can add workers without changing API.

**Q: Why Celery/Redis?**
> Decouples long-running downloads from API. Allows horizontal scaling. Redis provides caching + rate limiting.

**Q: What about persistence?**
> PostgreSQL stores job metadata. S3 stores files. Both persist across deployments.

**Q: Cost?**
> Free tier for demo (~$5-10/month if production). Scales with usage.

---

## Next Steps

1. **Push code to GitHub** (if not done)
2. **Create Railway/Render account**
3. **Add PostgreSQL + Redis services**
4. **Deploy from GitHub**
5. **Add environment variables**
6. **Run migrations**
7. **Test in browser**
8. **Send interviewer the URL** (e.g., https://media-download-api.railway.app)

**Total time: 15-20 minutes** ⏱️

