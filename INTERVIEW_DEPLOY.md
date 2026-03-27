# 🎯 Interview Deployment Quickstart

**Deploy your app for FREE in 15 minutes for interviews.**

---

## Fastest Path: Railway (Recommended)

### 1️⃣ Push Code to GitHub (3 min)

```bash
cd /Users/farhan/Desktop/priv/test

# Initialize git
git init
git config user.name "Your Name"
git config user.email "your@email.com"

git add .
git commit -m "initial: media download service"

# Create repo at https://github.com/new
# Then add remote (replace YOUR_USERNAME):
git remote add origin https://github.com/YOUR_USERNAME/media-download-service.git
git branch -M main
git push -u origin main
```

**✅ Code is now on GitHub**

---

### 2️⃣ Setup Railway (5 min)

1. Go to **[railway.app](https://railway.app)**
2. Click **"Start New Project"**
3. Sign in with GitHub
4. Click **"Deploy from GitHub repo"**
5. Select **YOUR_USERNAME/media-download-service**
6. Click **"Deploy"**

**Railway auto-detects your Dockerfile and starts building...**

---

### 3️⃣ Add PostgreSQL (2 min)

In your Railway project:
1. Click **"+ New"** → Select **"PostgreSQL"**
2. Wait 1 minute for database to start
3. Click **PostgreSQL** → **"Variables"**
4. **Copy** the `DATABASE_URL` line (whole thing)

---

### 4️⃣ Add Redis (2 min)

1. Click **"+ New"** → Select **"Redis"**
2. Wait 1 minute for Redis to start
3. Click **Redis** → **"Variables"**
4. **Copy** the `REDIS_URL` line

---

### 5️⃣ Setup Environment (3 min)

Click your **API service** → **"Variables"** tab → Add these:

```
DATABASE_URL=<PASTE FROM POSTGRESQL>
REDIS_URL=<PASTE FROM REDIS>
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_BUCKET_NAME=media-downloads-demo
S3_REGION=us-east-1
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_PUBLIC_URL=https://s3.amazonaws.com/media-downloads-demo
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=1
```

**Get S3 keys from AWS Free Tier:**
- Sign up: https://aws.amazon.com/free/ (free for 12 months)
- Create S3 bucket: `media-downloads-demo`
- Create IAM user with S3 access
- Copy Access Key ID and Secret Access Key
- Paste above

---

### 6️⃣ Run Migrations (1 min)

In Railway dashboard:
1. Click **API** service
2. Go to **"Deployments"** tab
3. Click latest deployment (should be green ✅)
4. Click **"Execute"** button
5. Paste and run:
```bash
alembic upgrade head
```

---

### 7️⃣ Test (1 min)

Get your URL from Railway dashboard (it's in the top right of API service):
```
https://YOUR-APP-NAME.up.railway.app
```

Test in browser:
```
https://YOUR-APP-NAME.up.railway.app/health
→ Should return: {"status":"ok"}
```

Open web UI:
```
https://YOUR-APP-NAME.up.railway.app/
```

**🎉 YOU'RE LIVE!**

---

## Interview Demo (2 minutes)

```bash
# 1. Open the URL in browser
https://YOUR-APP-NAME.up.railway.app/

# 2. Show API docs
https://YOUR-APP-NAME.up.railway.app/docs

# 3. Submit a test job
curl -X POST https://YOUR-APP-NAME.up.railway.app/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "worst"
  }'

# 4. Check status
# Copy the job_id from response, then:
curl https://YOUR-APP-NAME.up.railway.app/api/jobs/{job_id}

# 5. Watch progress increase in real-time
```

---

## Common Issues & Fixes

### ❌ "502 Bad Gateway"
```bash
# App is loading (can take 30 sec on first access)
# Solution: Wait 1 minute, refresh page
# If still fails: Check logs in Railway dashboard
```

### ❌ "Cannot connect to database"
```bash
# DATABASE_URL is wrong
# Solution: 
# 1. Delete the DATABASE_URL variable
# 2. Redeploy
# 3. Copy DATABASE_URL from PostgreSQL Variables again
# 4. Add it back
# 5. Redeploy again
```

### ❌ "Worker not processing jobs"
```bash
# REDIS_URL is wrong or missing
# Solution:
# 1. Verify REDIS_URL is set in BOTH API and Worker services
# 2. Copy it again from Redis service Variables tab
# 3. Redeploy both services
```

### ❌ "Cold start takes 10 seconds"
```bash
# This is normal on Railway free tier
# Solution: Open the URL once before interview
# After first access, it's fast (<500ms)
```

---

## 📊 Cost Breakdown

| Item | Cost | Notes |
|------|------|-------|
| PostgreSQL | FREE | Up to 1GB, 1 shared CPU |
| Redis | FREE | Up to 1GB |
| API Container | $5/mo credit | Railway gives $5 credit |
| Worker Container | Included | In the $5 credit |
| **TOTAL** | **FREE** | Everything covered by credit |

After free trial month, it's ~$0.10/day (very cheap).

---

## Full Details

For more details, see:
- **[FREE_DEPLOYMENT.md](FREE_DEPLOYMENT.md)** - All free options
- **[RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)** - Step-by-step Railway guide
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Commands & troubleshooting

---

## Send Interviewer This

```
Project URL: https://YOUR-APP-NAME.up.railway.app/
API Docs: https://YOUR-APP-NAME.up.railway.app/docs
GitHub: https://github.com/YOUR_USERNAME/media-download-service
```

They can test it live! 🚀

