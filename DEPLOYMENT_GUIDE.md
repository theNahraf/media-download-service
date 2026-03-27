# 📦 Media Download Service - Deployment Guide

Complete step-by-step instructions for deploying your scalable media download platform.

---

## Table of Contents
1. [Local Development (Docker)](#local-development-docker)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## Local Development (Docker)

### Step 1: Environment Setup
```bash
# Clone the repository (if needed)
cd /Users/farhan/Desktop/priv/test

# Create environment file from example
cp .env.example .env
```

**Edit `.env` with your configuration:**
```env
# Database
POSTGRES_USER=mediadown
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=mediadownload
DATABASE_URL=postgresql://mediadown:your_secure_password_here@postgres:5432/mediadownload

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO / S3
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET_NAME=media-downloads
S3_REGION=us-east-1
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_PUBLIC_URL=http://localhost:9000  # Change to your server IP for mobile testing

# API
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4
```

### Step 2: Build & Start Services
```bash
# Build all containers
docker-compose build

# Start all services in background
docker-compose up -d

# View logs in real-time
docker-compose logs -f

# Check service health
docker-compose ps
```

**Expected Output:**
```
NAME       STATUS           PORTS
api        Up (healthy)     0.0.0.0:8000->8000/tcp
worker     Up               
postgres   Up (healthy)     0.0.0.0:5432->5432/tcp
redis      Up (healthy)     0.0.0.0:6379->6379/tcp
minio      Up               0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp
flower     Up               0.0.0.0:5555->5555/tcp
```

### Step 3: Initialize Database
```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify tables were created
docker-compose exec postgres psql -U mediadown -d mediadownload -c "\dt"
```

### Step 4: Verify Services
Open these URLs in your browser:

| Service | URL | Purpose |
|---------|-----|---------|
| **Web UI** | http://localhost:8000 | Main download interface |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **MinIO Console** | http://localhost:9001 | S3 bucket management (user: `minioadmin` / pass: `minioadmin`) |
| **Flower Dashboard** | http://localhost:5555 | Celery worker monitoring |

### Step 5: Test the System
```bash
# Test API health
curl http://localhost:8000/health

# Test job creation (submit a download)
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best"
  }'

# Expected response:
# {
#   "job_id": "abc123def456",
#   "status": "pending",
#   "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
# }
```

---

## Pre-Deployment Checklist

Before deploying to staging/production, verify:

- [ ] **Environment Variables:** All `.env` values are set (no defaults remain)
- [ ] **Database:** `alembic upgrade head` has been run successfully
- [ ] **S3 Bucket:** Created in MinIO/AWS and permissions are correct
- [ ] **Redis:** Connection string verified and password set (if using auth)
- [ ] **SSL Certificates:** Obtained (e.g., from Let's Encrypt via Certbot)
- [ ] **Domain Name:** DNS records point to your deployment server
- [ ] **Docker Images:** All Dockerfiles build without errors
- [ ] **Secrets Management:** Passwords stored in secure vault (not in git)
- [ ] **Backups:** Postgres dump schedule configured
- [ ] **Monitoring:** Logging & alerting tools in place

---

## Staging Deployment

### Option A: Deploy to a Linux Server (VPS / EC2)

#### Step 1: Provision Server
```bash
# SSH into your server
ssh user@staging.example.com

# Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.25.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Step 2: Clone Repository
```bash
# Clone from your repository
git clone https://github.com/yourname/media-download-service.git
cd media-download-service

# Create production .env
nano .env
# (Enter your staging credentials)
```

#### Step 3: Configure Reverse Proxy (Nginx)
Create `/etc/nginx/sites-available/api`:
```nginx
server {
    listen 80;
    server_name api-staging.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api-staging.example.com;

    ssl_certificate /etc/letsencrypt/live/api-staging.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api-staging.example.com/privkey.pem;

    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long downloads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 4: Setup SSL Certificate (Let's Encrypt)
```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx -y

sudo certbot certonly --standalone \
  -d api-staging.example.com \
  --email admin@example.com \
  --agree-tos \
  --non-interactive

# Auto-renewal
echo "0 3 * * * certbot renew --quiet" | sudo crontab -
```

#### Step 5: Start Services
```bash
# Build images
docker-compose build

# Start in production mode
docker-compose up -d

# Initialize database
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f
```

#### Step 6: Configure Database Backups
```bash
# Create backup script
nano backup.sh
```

**backup.sh:**
```bash
#!/bin/bash
BACKUP_DIR="/backups/postgres"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

docker-compose exec -T postgres pg_dump \
  -U mediadown \
  mediadownload > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/backup_$TIMESTAMP.sql"
```

```bash
# Make executable
chmod +x backup.sh

# Schedule daily backups at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /home/user/media-download-service/backup.sh") | crontab -
```

---

## Production Deployment

### Option A: AWS Deployment (Recommended)

#### Architecture Overview
```
CloudFront (CDN)
    ↓
ALB (Application Load Balancer)
    ↓
ECS Fargate Cluster
    ├── FastAPI Tasks
    └── Celery Worker Tasks
    
Managed Services:
├── RDS PostgreSQL (Multi-AZ)
├── ElastiCache Redis
├── S3 (Object Storage)
└── CloudWatch (Monitoring)
```

#### Step 1: Setup AWS Infrastructure

**1a. Create VPC & Security Groups**
```bash
# Using AWS CLI
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region us-east-1

# Create security groups for:
# - ALB: Allow ports 80, 443 from 0.0.0.0/0
# - ECS: Allow ports 8000, 8001 from ALB security group
# - RDS: Allow port 5432 from ECS security group
# - ElastiCache: Allow port 6379 from ECS security group
```

**1b. Create RDS PostgreSQL**
```bash
aws rds create-db-instance \
  --db-instance-identifier media-download-prod \
  --db-instance-class db.t4g.small \
  --engine postgres \
  --engine-version 16.1 \
  --master-username mediadown \
  --master-user-password "$(openssl rand -base64 32)" \
  --allocated-storage 50 \
  --storage-type gp3 \
  --multi-az \
  --backup-retention-period 30 \
  --region us-east-1
```

**1c. Create ElastiCache Redis**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id media-download-redis \
  --cache-node-type cache.t4g.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --auto-minor-version-upgrade \
  --region us-east-1
```

**1d. Create S3 Bucket**
```bash
aws s3 mb s3://media-downloads-prod-us-east-1 \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket media-downloads-prod-us-east-1 \
  --versioning-configuration Status=Enabled

# Block public access (use signed URLs)
aws s3api put-public-access-block \
  --bucket media-downloads-prod-us-east-1 \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable lifecycle policies (delete old files after 30 days)
cat > lifecycle.json << 'EOF'
{
  "Rules": [
    {
      "Id": "DeleteOldFiles",
      "Status": "Enabled",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket media-downloads-prod-us-east-1 \
  --lifecycle-configuration file://lifecycle.json
```

#### Step 2: Create ECR Repositories
```bash
# API image
aws ecr create-repository \
  --repository-name media-download-api \
  --region us-east-1

# Worker image
aws ecr create-repository \
  --repository-name media-download-worker \
  --region us-east-1
```

#### Step 3: Build & Push Docker Images
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -f Dockerfile.api \
  -t 123456789.dkr.ecr.us-east-1.amazonaws.com/media-download-api:latest .

docker build -f Dockerfile.worker \
  -t 123456789.dkr.ecr.us-east-1.amazonaws.com/media-download-worker:latest .

# Push to ECR
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/media-download-api:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/media-download-worker:latest
```

#### Step 4: Create ECS Cluster & Services

**Create Cluster:**
```bash
aws ecs create-cluster --cluster-name media-download-prod
```

**Create Task Definitions:**
```bash
# API Task Definition
aws ecs register-task-definition \
  --family media-download-api \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 512 \
  --memory 1024 \
  --container-definitions '[{
    "name": "api",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/media-download-api:latest",
    "portMappings": [{"containerPort": 8000, "hostPort": 8000}],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql://mediadown:PASSWORD@rds-endpoint:5432/mediadownload"},
      {"name": "REDIS_URL", "value": "redis://elasticache-endpoint:6379/0"},
      {"name": "S3_ENDPOINT_URL", "value": "https://s3.amazonaws.com"},
      {"name": "S3_BUCKET_NAME", "value": "media-downloads-prod-us-east-1"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/media-download-api",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]'

# Worker Task Definition (similar)
# ... (repeat for worker)
```

**Create ECS Service:**
```bash
aws ecs create-service \
  --cluster media-download-prod \
  --service-name api \
  --task-definition media-download-api \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=DISABLED}"
```

#### Step 5: Setup CloudFront CDN
```bash
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "'"$(date +%s)"'",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "APIOrigin",
        "DomainName": "alb-xxx.us-east-1.elb.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "https-only"
        }
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "APIOrigin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "AllowedMethods": {
        "Quantity": 7,
        "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
      },
      "CachePolicyId": "4135ea3d-c35d-46eb-81d7-edf2780556d7",
      "OriginRequestPolicyId": "216adef5-5c7f-47e4-b989-5492eafa07d3"
    },
    "Enabled": true
  }'
```

#### Step 6: Setup Monitoring & Logging
```bash
# Create CloudWatch Log Groups
aws logs create-log-group --log-group-name /ecs/media-download-api
aws logs create-log-group --log-group-name /ecs/media-download-worker

# Create Alarms
aws cloudwatch put-metric-alarm \
  --alarm-name api-high-cpu \
  --alarm-description "Alert when API CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## Post-Deployment Verification

### Step 1: Health Checks
```bash
# API health
curl https://api.example.com/health

# Database connection
curl https://api.example.com/health/db

# Redis connection
curl https://api.example.com/health/redis

# S3 connectivity
curl https://api.example.com/health/storage
```

### Step 2: Submit Test Job
```bash
curl -X POST https://api.example.com/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best"
  }' \
  -H "Authorization: Bearer YOUR_API_KEY"

# Track job
curl https://api.example.com/api/jobs/{job_id} \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Step 3: Verify Worker Processing
- Open Flower Dashboard: `https://monitoring.example.com:5555`
- Should show active workers and completed tasks

### Step 4: Test S3 Upload
```bash
# List bucket contents
aws s3 ls s3://media-downloads-prod-us-east-1/

# Verify file access with signed URL
aws s3 presign s3://media-downloads-prod-us-east-1/sample.mp4
```

---

## Monitoring & Troubleshooting

### Common Issues & Solutions

#### Issue: Worker tasks not processing
```bash
# Check Redis connection
docker-compose exec redis redis-cli ping
# Expected: PONG

# Check Celery workers
docker-compose logs worker | grep -i error

# Restart workers
docker-compose restart worker
```

#### Issue: Database migration failed
```bash
# Check migration status
docker-compose exec api alembic current

# View migration history
docker-compose exec api alembic history

# Rollback if needed
docker-compose exec api alembic downgrade -1
```

#### Issue: S3 upload failures
```bash
# Verify credentials
aws s3 ls --profile default

# Check bucket permissions
aws s3api get-bucket-acl --bucket media-downloads-prod

# Test with AWS CLI
echo "test" | aws s3 cp - s3://media-downloads-prod/test.txt
```

#### Issue: High memory usage
```bash
# Scale workers down
docker-compose down

# Rebuild with fewer workers in .env (WORKERS=2)
nano .env
docker-compose up -d
```

### Monitoring Dashboard Setup

**CloudWatch Custom Metrics:**
```python
# In your FastAPI app (api/main.py)
import boto3

cloudwatch = boto3.client('cloudwatch')

@app.post("/api/jobs")
async def create_job(request: JobRequest):
    # Your job creation logic...
    
    cloudwatch.put_metric_data(
        Namespace='MediaDownloadService',
        MetricData=[{
            'MetricName': 'JobsCreated',
            'Value': 1,
            'Unit': 'Count'
        }]
    )
```

---

## Rollback & Recovery

### Database Backup Recovery
```bash
# List available backups
ls -la /backups/postgres/

# Restore from backup
docker-compose exec postgres psql -U mediadown \
  < /backups/postgres/backup_20240115_020000.sql
```

### Docker Image Rollback
```bash
# View image history
docker images media-download-api

# Restart with previous tag
docker-compose down
# Edit docker-compose.yml to use previous tag
docker-compose up -d
```

---

## Security Best Practices

1. **Secrets Management:** Use AWS Secrets Manager or HashiCorp Vault
   ```bash
   aws secretsmanager create-secret \
     --name media-download/prod \
     --secret-string file://secrets.json
   ```

2. **Database Encryption:** Enable RDS encryption at rest
3. **Network Security:** Use VPC endpoints instead of public IPs
4. **API Authentication:** Implement OAuth2 or JWT tokens
5. **Rate Limiting:** Already configured via Redis token bucket in FastAPI
6. **Log Rotation:** Configure CloudWatch log retention (30 days)
7. **HTTPS Only:** Force SSL/TLS on all endpoints

---

## Scaling Guidelines

| Metric | Action |
|--------|--------|
| API CPU > 70% | Add 1 Fargate task |
| Queue depth > 1000 | Add 2 workers |
| Database connections > 20 | Increase RDS instance size |
| Redis memory > 80% | Increase ElastiCache node size |

---

## Support & Documentation

- **Flower Monitoring:** https://your-domain.com:5555
- **API Docs:** https://your-domain.com/docs
- **Logs:** CloudWatch or `docker-compose logs`
- **Issue Tracking:** Create GitHub issues with `docker-compose ps` output

