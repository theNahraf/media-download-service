# 🚀 Quick Deployment Reference

## 3-Step Local Deployment (First Time)

```bash
# Step 1: Setup
cd /Users/farhan/Desktop/priv/test
cp .env.example .env
# Edit .env with your values (important: change passwords)
nano .env

# Step 2: Deploy
./deploy.sh local

# Step 3: Verify
# Open http://localhost:8000 in browser
# Open http://localhost:5555 for worker dashboard
```

---

## Quick Commands

### View Logs
```bash
docker-compose logs -f              # All services
docker-compose logs -f api          # Just API
docker-compose logs -f worker       # Just worker
docker-compose logs -f postgres     # Just database
```

### Check Service Status
```bash
docker-compose ps                   # Show all containers
docker-compose exec api echo "OK"   # Test API container
docker-compose exec postgres psql -U mediadown -d mediadownload -c "SELECT version();"
```

### Database Operations
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Check migration status
docker-compose exec api alembic current

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "describe change"
```

### Restart Services
```bash
docker-compose restart api          # Restart API only
docker-compose restart worker       # Restart workers
docker-compose down && docker-compose up -d  # Full restart
```

### Clean Everything (WARNING: Deletes data)
```bash
docker-compose down -v              # Remove containers and volumes
docker-compose build --no-cache     # Rebuild from scratch
docker-compose up -d                # Start fresh
```

### Access Database Directly
```bash
docker-compose exec postgres psql -U mediadown -d mediadownload
```

Interactive SQL examples:
```sql
-- Check tables
\dt

-- Count jobs
SELECT COUNT(*) FROM jobs;

-- View recent jobs
SELECT id, url, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 5;

-- Exit
\q
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Create job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "best"}'

# Get job status
curl http://localhost:8000/api/jobs/{job_id}

# List jobs
curl http://localhost:8000/api/jobs
```

### Monitor Workers
```bash
# View active tasks
docker-compose exec worker celery -A worker.celery_app inspect active

# View registered tasks
docker-compose exec worker celery -A worker.celery_app inspect registered

# View worker stats
docker-compose exec worker celery -A worker.celery_app inspect stats
```

---

## Deployment Environments

### Development (Local Docker)
- **Command:** `./deploy.sh local`
- **Duration:** ~2 minutes
- **Data:** Ephemeral (resets with `docker-compose down`)
- **URL:** http://localhost:8000

### Staging (VPS)
- **Command:** `export STAGING_SERVER=user@staging.example.com && ./deploy.sh staging`
- **Duration:** ~5 minutes
- **Data:** Persistent (RDS backup configured)
- **URL:** https://api-staging.example.com

### Production (AWS ECS)
- **Command:** `./deploy.sh production`
- **Duration:** ~10 minutes (blue-green deployment)
- **Data:** Persistent (Multi-AZ RDS with daily backups)
- **URL:** https://api.example.com

---

## Common Troubleshooting

### Workers Not Processing Jobs

**Problem:** Jobs stay in "pending" status  
**Solution:**
```bash
# Check if Redis is accessible
docker-compose exec redis redis-cli ping
# Expected: PONG

# Check worker logs
docker-compose logs worker | tail -50

# Restart workers
docker-compose restart worker

# Verify task is received
docker-compose exec worker celery -A worker.celery_app inspect active
```

### Database Migration Fails

**Problem:** `alembic upgrade head` fails  
**Solution:**
```bash
# Check current migration
docker-compose exec api alembic current

# View history
docker-compose exec api alembic history

# Roll back one version
docker-compose exec api alembic downgrade -1

# Then try upgrade again
docker-compose exec api alembic upgrade head
```

### S3/MinIO Upload Fails

**Problem:** Files not appearing in MinIO  
**Solution:**
```bash
# Check MinIO is accessible
curl http://localhost:9000/minio/health/live
# Expected: 200 OK

# Check worker logs
docker-compose logs worker | grep -i s3

# Verify bucket exists
docker-compose exec worker python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://minio:9000', 
                  aws_access_key_id='minioadmin',
                  aws_secret_access_key='minioadmin')
print(s3.list_buckets())"
```

### High Memory Usage

**Problem:** Container OOMKilled or very slow  
**Solution:**
```bash
# Check memory usage
docker stats

# Reduce worker count in .env
nano .env
# Change: WORKERS=2  (from WORKERS=4)

# Restart
docker-compose restart worker

# Monitor
docker stats worker
```

### Port Already in Use

**Problem:** `Error: bind: address already in use`  
**Solution:**
```bash
# Find what's using the port (e.g., 8000)
lsof -i :8000
# Kill it
kill -9 <PID>

# Or change ports in docker-compose.yml
nano docker-compose.yml
# Change: 8001:8000 (use 8001 instead of 8000)

# Restart
docker-compose up -d
```

---

## Deployment Checklist (TL;DR)

### Before Local Deployment
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] `.env` file created and edited
- [ ] 10+ GB free disk space

### Before Staging Deployment
- [ ] VPS provisioned
- [ ] SSH access verified
- [ ] Domain DNS configured
- [ ] SSL certificate obtained
- [ ] Repository cloned on server
- [ ] `.env` created with production values

### Before Production Deployment
- [ ] AWS account configured
- [ ] VPC + subnets created
- [ ] RDS PostgreSQL running (Multi-AZ)
- [ ] ElastiCache Redis running
- [ ] S3 bucket created
- [ ] ECR repositories created
- [ ] ECS cluster created
- [ ] ALB configured
- [ ] CloudFront distribution created
- [ ] Domain DNS points to CloudFront
- [ ] CloudWatch log groups created
- [ ] Backups configured

---

## Useful URLs During Deployment

| Component | Local URL | Production URL |
|-----------|-----------|----------------|
| Web UI | http://localhost:8000 | https://api.example.com |
| API Docs | http://localhost:8000/docs | https://api.example.com/docs |
| MinIO | http://localhost:9001 | AWS S3 Console |
| Flower | http://localhost:5555 | https://monitoring.example.com:5555 |
| Postgres | localhost:5432 | RDS endpoint |
| Redis | localhost:6379 | ElastiCache endpoint |

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `.env` | Environment variables (passwords, endpoints) |
| `docker-compose.yml` | Service definitions and networking |
| `Dockerfile.api` | FastAPI container recipe |
| `Dockerfile.worker` | Celery worker container recipe |
| `api/main.py` | FastAPI application entry point |
| `worker/celery_app.py` | Celery configuration |
| `alembic/` | Database migrations |
| `DEPLOYMENT_GUIDE.md` | Detailed deployment instructions |
| `DEPLOYMENT_CHECKLIST.md` | Full pre-deployment checklist |
| `deploy.sh` | Automated deployment script |

---

## Emergency Commands

### Stop Everything
```bash
docker-compose down
# Or (harder stop):
docker-compose kill
```

### Reset Everything (WARNING: Deletes all data!)
```bash
docker-compose down -v
docker system prune -a
docker-compose build
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Get Inside a Container
```bash
docker-compose exec api bash          # Shell in API
docker-compose exec worker bash       # Shell in worker
docker-compose exec postgres bash     # Shell in database
```

### View Real-Time Metrics
```bash
docker stats --no-stream    # One-time snapshot
docker stats                # Live updating
```

---

## Success Indicators

✅ **Deployment is successful when:**

1. All containers are healthy:
   ```bash
   docker-compose ps | grep -c healthy
   # Should show 3 (postgres, redis, and api)
   ```

2. API responds:
   ```bash
   curl http://localhost:8000/health
   # Expected: 200 OK
   ```

3. Test job processes:
   - Submit job via Web UI
   - Monitor in Flower dashboard
   - File appears in MinIO
   - Download link works

4. No error logs:
   ```bash
   docker-compose logs | grep -i error
   # Should return nothing
   ```

---

## Need Help?

1. **Check logs:** `docker-compose logs -f`
2. **Read docs:** See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
3. **Verify checklist:** See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
4. **Test manually:** Use curl commands above
5. **Clean restart:** `docker-compose down -v && docker-compose up -d`

