# Railway Deployment - Step-by-Step

Complete guide to deploy to Railway in **5 minutes** for your interview.

---

## Step 0: Prerequisites

- [GitHub Account](https://github.com) (free)
- [Railway Account](https://railway.app) (sign in with GitHub)
- Code committed to GitHub repo

---

## Step 1: Create GitHub Repository (5 min)

```bash
# Go to your project
cd /Users/farhan/Desktop/priv/test

# Initialize git if not done
git init
git add .
git commit -m "Initial commit: Media Download Service"

# Create repo on GitHub: https://github.com/new
# Name it: media-download-service
# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/media-download-service.git
git branch -M main
git push -u origin main
```

---

## Step 2: Create Railway Services

### 2a. Create PostgreSQL Database

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"** → **"Provision PostgreSQL"**
3. Wait 1-2 minutes for database to start
4. Click **PostgreSQL** service → **"Variables"** tab
5. **Copy** the `DATABASE_URL` (highlighted)
   - Format: `postgresql://user:pass@host:port/dbname`
   - Save it, you'll need it in Step 3

### 2b. Create Redis Service

1. Still in your project, click **"+ New"**
2. Select **"Redis"**
3. Wait for Redis to start
4. Click **Redis** service → **"Variables"** tab
5. **Copy** the `REDIS_URL` (highlighted)
   - Format: `redis://:password@host:port`
   - Save it, you'll need it in Step 3

### 2c. Deploy Your App

1. Click **"+ New"**
2. Select **"Deploy from GitHub repo"**
3. Select **YOUR_USERNAME/media-download-service**
4. Click **"Deploy"**
5. Railway will auto-detect the Dockerfile
   - It will ask which services to deploy
   - Select both **api** and **worker**

---

## Step 3: Configure Environment Variables

### 3a. Set Variables in Railway Dashboard

Click your **API** service → **"Variables"** tab → Add these:

```
DATABASE_URL=postgresql://...     [PASTE from Step 2a]
REDIS_URL=redis://...             [PASTE from Step 2b]

S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=media-downloads-interview
S3_REGION=us-east-1
S3_ACCESS_KEY=                    [Get from AWS below]
S3_SECRET_KEY=                    [Get from AWS below]
S3_PUBLIC_URL=https://s3.amazonaws.com/media-downloads-interview

API_HOST=0.0.0.0
API_PORT=8000
WORKERS=2
RATE_LIMIT_PER_HOUR=30
DOWNLOAD_EXPIRY_HOURS=24
MAX_FILE_SIZE_MB=512
SIGNED_URL_EXPIRY_SECONDS=3600
```

Do the same for **Worker** service.

### 3b. Get AWS S3 Keys (5 min)

If you don't have AWS account, create one: https://aws.amazon.com/free/

```bash
# 1. Login to AWS Console
# 2. Go to S3 → Create Bucket
#    Name: media-downloads-interview-demo
#    Region: us-east-1
#    Click "Create bucket"

# 3. Go to IAM → Users → Add User
#    Name: media-download-service
#    Access type: Programmatic access
#    Next: Permissions → Attach inline policy

# 4. JSON Policy (paste this):
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::media-downloads-interview-demo",
                "arn:aws:s3:::media-downloads-interview-demo/*"
            ]
        }
    ]
}

# 5. Click "Create user"
# 6. Download CSV with Access Key ID and Secret Access Key
# 7. Use these in Railway variables above
```

---

## Step 4: Run Database Migrations

### 4a. Connect to Container Terminal

1. In Railway dashboard, click **API** service
2. Go to **"Deployments"** tab
3. Click the green checkmark (latest deployment)
4. Click **"Execute"** button

### 4b. Run Migrations

In the terminal, run:
```bash
cd /app
alembic upgrade head
```

Wait for migrations to complete (~10 seconds).

---

## Step 5: Verify Deployment

### 5a. Get Your App URL

1. In Railway dashboard, click **API** service
2. On the right, you'll see a URL like: `https://media-download-api-production.up.railway.app`
3. Copy this URL

### 5b. Test API is Working

```bash
# Replace with your Railway URL
curl https://YOUR_RAILWAY_URL.up.railway.app/health

# Expected response:
# {"status":"ok"}
```

### 5c. Open Web UI

Open in browser:
```
https://YOUR_RAILWAY_URL.up.railway.app/
```

You should see the download interface! 🎉

---

## Step 6: Test End-to-End (Optional)

### Test Job Submission

```bash
# Replace with your URL
curl -X POST https://YOUR_RAILWAY_URL.up.railway.app/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "worst"
  }'
```

You should get back:
```json
{
  "job_id": "abc123def456",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00"
}
```

### Check Job Status

```bash
curl https://YOUR_RAILWAY_URL.up.railway.app/api/jobs/abc123def456
```

Watch the `progress` field increase as the worker processes it.

---

## 🚀 Your Interview Demo (2 minutes)

### Demo Script

```
Good morning! I built a scalable media download service.

[SHOW DASHBOARD]
This is the web UI - you can submit a video URL and it 
downloads asynchronously.

[SHOW API DOCS]
Open /docs - here's the Swagger API documentation.
The system is fully RESTful.

[SUBMIT A JOB]
Let me submit a download request...
curl -X POST https://[YOUR_URL]/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "...", "format": "worst"}'

[SHOW JOB ID]
It returns a job ID immediately - no blocking!
The download happens in the background.

[EXPLAIN ARCHITECTURE]
- FastAPI for the async API
- Celery workers for heavy processing
- Redis for job queue + caching
- PostgreSQL for persistence
- S3 for storage

[SHOW METRICS]
The system is stateless and horizontally scalable.
Each worker can process jobs independently.
We use Redis for deduplication - same URL won't download twice.

[SHOW CODE]
Here's the code on GitHub - fully containerized,
ready for Kubernetes or any cloud platform.
```

---

## ⚠️ Things to Know Before Interview

### Cold Start Issue
- **On first access**, app might take 5-10 seconds to wake up
- **Solution:** Open the URL once before interview starts, or warn interviewer
- **After first access:** Responses are instant (<500ms)

### Free Tier Limits
- **RAM:** 512MB (for 2 workers, might be tight)
- **If out of memory:** Reduce WORKERS to 1 in variables
- **CPU:** Shared (low performance)
- **But:** Good enough for interview demo

### Worker Processing Time
- **Small video:** 30-60 seconds (free tier is slow)
- **Solution:** Use a small video URL for demo
- Or download locally and have file ready in S3

### Internet Connection
- Ensure your WiFi is stable
- Have mobile data as backup
- Test URL before interview call

---

## 🔧 Quick Troubleshooting

### "502 Bad Gateway"
```
Likely cause: App crashed or taking too long to start
Solution: 
1. Check Railway logs (Deployments tab)
2. Look for database connection error
3. Verify DATABASE_URL is correct
4. Redeploy: Click latest deployment → "Redeploy"
```

### "Cannot connect to database"
```
Likely cause: DATABASE_URL is wrong or database not ready
Solution:
1. Copy DATABASE_URL again from PostgreSQL service Variables tab
2. Paste into API service Variables tab
3. Redeploy
4. Wait 30 seconds, try again
```

### "Worker not processing jobs"
```
Likely cause: REDIS_URL missing or wrong
Solution:
1. Verify REDIS_URL in both API and Worker service variables
2. Check they match exactly
3. Restart both services (Redeploy button)
```

### "S3 upload fails"
```
Likely cause: AWS keys are wrong or invalid
Solution:
1. Go to AWS Console → IAM → Users
2. Verify user still exists
3. Check S3 bucket still exists
4. Regenerate keys if needed
5. Update in Railway variables
```

---

## 📋 Pre-Interview Checklist

- [ ] GitHub repo created and public
- [ ] Railway project created with PostgreSQL + Redis + App
- [ ] All environment variables set in Railway
- [ ] Migrations run successfully (`alembic upgrade head`)
- [ ] `/health` endpoint returns 200 OK
- [ ] Web UI loads in browser
- [ ] `/docs` Swagger UI accessible
- [ ] Test job submission works
- [ ] Download link is generated
- [ ] You can open and play downloaded file

If all these pass, you're ready! ✅

---

## Interview URL to Send

Once deployed, give interviewer this URL:

```
https://YOUR_RAILWAY_APP_NAME.up.railway.app/

(You can also add /docs for the API documentation)
```

They can:
- See the web UI
- Read the API docs
- Test the API directly
- See the running system live

---

## After Interview

### Keep It Running
- Railway charges $5/month by default (very cheap)
- Or delete project to avoid charges

### Save Your Code
```bash
# Your code is already on GitHub
# Just keep the repo public so they can see it

# If you need to share a walkthrough:
git log --oneline  # Show commit history
git show HEAD      # Show latest commit
```

### Get Feedback Link
Send interviewer the GitHub repo:
```
https://github.com/YOUR_USERNAME/media-download-service
```

They can review code, architecture, and deployment strategy.

---

## Expected Questions

**Q: Why did you choose Railway?**
> Free tier with $5/month credit. Good for demos. Has all the services we need (Postgres, Redis, Docker).

**Q: How would you deploy to production?**
> Same architecture on AWS ECS/Fargate. RDS for database, ElastiCache for Redis, S3 for storage.

**Q: Can this handle scale?**
> Yes. Workers are stateless, so we can add more. Queue decouples API from processing.

**Q: What about database performance?**
> Free tier is slow but fine for demo. Production would use RDS with proper indexing.

---

## 🎉 You're Done!

In 20 minutes, you have a live, production-like system deployed.
Ready to impress! 💪

