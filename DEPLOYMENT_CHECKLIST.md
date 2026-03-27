# 🎯 Deployment Checklist

## Pre-Deployment Phase

### Development Environment
- [ ] All code committed to git
- [ ] No hardcoded secrets in code
- [ ] All tests passing locally
- [ ] Docker images build without warnings
- [ ] `.env.example` file updated with all required variables

### Local Docker Testing (Dev/Staging)
- [ ] Run `docker-compose build` successfully
- [ ] Run `docker-compose up -d` successfully
- [ ] All services healthy: `docker-compose ps`
- [ ] Database migrations pass: `docker-compose exec api alembic upgrade head`
- [ ] Can access web UI at http://localhost:8000
- [ ] Can access API docs at http://localhost:8000/docs
- [ ] Can access Flower at http://localhost:5555
- [ ] Can access MinIO at http://localhost:9001
- [ ] Test download workflow completes end-to-end
- [ ] No errors in logs: `docker-compose logs`

### Environment Configuration
- [ ] POSTGRES_PASSWORD is set to secure value (>16 chars)
- [ ] MINIO_ROOT_PASSWORD is set to secure value
- [ ] S3_PUBLIC_URL matches deployment server IP/domain
- [ ] DATABASE_URL connection string is correct
- [ ] REDIS_URL is reachable and authenticated (if password set)
- [ ] CELERY_BROKER_URL matches Redis endpoint
- [ ] API workers count appropriate for server capacity

### Infrastructure Preparation
- [ ] VPS/Cloud instance provisioned and accessible
- [ ] SSH key configured and tested
- [ ] Firewall rules configured (80, 443, 5555 for Flower)
- [ ] Domain name registered and DNS configured
- [ ] SSL certificate obtained (Let's Encrypt or custom)
- [ ] Database backup strategy planned
- [ ] Log aggregation service configured

---

## Staging Deployment Phase

### VPS Setup
- [ ] Docker installed and running
- [ ] Docker Compose installed (v2.0+)
- [ ] Nginx installed for reverse proxy
- [ ] SSL certificates installed in `/etc/letsencrypt/`
- [ ] Nginx config created and tested (`nginx -t`)
- [ ] Git repository cloned on server

### Deployment
- [ ] `.env` file created with production values (not in git)
- [ ] `docker-compose build` completes on server
- [ ] `docker-compose up -d` completes successfully
- [ ] Database migrations run: `docker-compose exec api alembic upgrade head`
- [ ] S3 bucket created and accessible from container
- [ ] Backup script created and tested

### Post-Deployment Verification
- [ ] Health check passes: `curl https://api-staging.example.com/health`
- [ ] API docs accessible: https://api-staging.example.com/docs
- [ ] Flower accessible: https://api-staging.example.com:5555
- [ ] Test job submission works
- [ ] Worker processes job successfully
- [ ] File uploaded to S3/MinIO
- [ ] Signed URL generated and file downloadable
- [ ] No ERROR or CRITICAL logs in past 5 minutes

### Monitoring Setup
- [ ] CloudWatch/Prometheus metrics configured
- [ ] Log aggregation tool connected (Datadog/ELK/CloudWatch)
- [ ] Uptime monitoring enabled
- [ ] Email alerts configured
- [ ] Slack/PagerDuty integration configured

---

## Production Deployment Phase

### AWS Infrastructure (if using AWS)
- [ ] VPC created with public/private subnets
- [ ] RDS PostgreSQL instance created (Multi-AZ)
  - [ ] Automated backups enabled (30+ days)
  - [ ] Enhanced monitoring enabled
  - [ ] Parameter group configured
- [ ] ElastiCache Redis cluster created
  - [ ] Automatic failover enabled (if multi-node)
- [ ] S3 bucket created with proper permissions
  - [ ] Versioning enabled
  - [ ] Lifecycle policy configured (30-day expiry)
  - [ ] Public access blocked
- [ ] ECR repositories created for API and Worker
- [ ] ECS Cluster created
- [ ] ALB created with health checks
- [ ] CloudFront distribution created
- [ ] CloudWatch log groups created
- [ ] IAM roles and policies configured

### Docker Images
- [ ] Docker images tagged with version number
- [ ] Images pushed to ECR
- [ ] `docker-compose.yml` uses ECR URIs
- [ ] Image scanning enabled in ECR (vulnerability check)

### Secrets Management
- [ ] Database password stored in AWS Secrets Manager
- [ ] S3 access keys stored in Secrets Manager
- [ ] Redis password stored in Secrets Manager
- [ ] API keys/tokens stored in Secrets Manager
- [ ] ECS task role has access to Secrets Manager
- [ ] No secrets in environment variables or code

### Deployment
- [ ] ECS task definitions updated with latest image tags
- [ ] Environment variables match production requirements
- [ ] Replica count set to 2+ for high availability
- [ ] Auto-scaling policies configured
- [ ] Load balancer health checks configured
- [ ] DNS updated to point to CloudFront/ALB
- [ ] SSL certificates renewed/updated

### Post-Deployment Verification
- [ ] Health check endpoint returns 200 OK
- [ ] Database connectivity verified
- [ ] S3 operations functional
- [ ] Redis connectivity verified
- [ ] API documentation accessible at /docs
- [ ] CloudFront caching working (check X-Cache header)
- [ ] SSL certificate valid (no browser warnings)
- [ ] Rate limiting functional
- [ ] CORS headers correct
- [ ] CloudWatch logs flowing in
- [ ] CloudWatch alarms active

### Security Hardening
- [ ] Web Application Firewall (WAF) rules configured
- [ ] VPC security groups restricted to necessary ports
- [ ] Database security group restricts to ECS only
- [ ] ElastiCache security group restricts to ECS only
- [ ] S3 bucket policy reviewed
- [ ] IAM policies follow least privilege
- [ ] CloudTrail enabled for audit logging
- [ ] Config rules enabled for compliance monitoring
- [ ] Backup encryption enabled
- [ ] Data encryption in transit (TLS) enabled
- [ ] Data encryption at rest enabled (RDS, S3)

### Data Migration
- [ ] Backup taken from staging database
- [ ] Backup tested for restore
- [ ] Historical data migrated if applicable
- [ ] Data validation passed
- [ ] Staging database backed up before final sync

### Monitoring & Alerting
- [ ] CloudWatch dashboards created
- [ ] Alarms configured for:
  - [ ] API CPU > 70%
  - [ ] API memory > 80%
  - [ ] Queue depth > 1000
  - [ ] Database CPU > 70%
  - [ ] RDS storage > 80%
  - [ ] Worker task failures
  - [ ] Failed job tasks
- [ ] SNS topics configured for alerts
- [ ] Email notifications working
- [ ] Slack/PagerDuty integration verified

### Backup & Recovery
- [ ] Automated RDS backups enabled
- [ ] Backup retention set to 30+ days
- [ ] S3 versioning enabled
- [ ] Restore test completed successfully
- [ ] Disaster recovery plan documented

### Documentation
- [ ] Deployment documentation updated
- [ ] Runbook created for common operations
- [ ] Troubleshooting guide updated
- [ ] Team trained on monitoring/alerting tools
- [ ] Incident response plan documented
- [ ] Escalation contacts listed

---

## Post-Production Monitoring (Ongoing)

### Daily Checks
- [ ] No critical errors in logs
- [ ] All services healthy
- [ ] Queue processing normally
- [ ] Average response time < 2s
- [ ] Job success rate > 95%

### Weekly Checks
- [ ] Backup integrity verified
- [ ] Disk usage trending normally
- [ ] No security alerts
- [ ] Performance metrics normal
- [ ] Review CloudWatch dashboards

### Monthly Checks
- [ ] Full backup restore test
- [ ] Security audit (logs, access)
- [ ] Update Docker base images
- [ ] Review cost optimization
- [ ] Capacity planning review

---

## Rollback Procedure

If production issues occur:

1. **Identify Issue**
   ```bash
   docker-compose logs worker | tail -100
   docker-compose ps
   ```

2. **Revert to Previous Image**
   ```bash
   # Update docker-compose.yml to use previous image tag
   docker-compose pull
   docker-compose up -d
   ```

3. **Verify Health**
   ```bash
   curl https://api.example.com/health
   ```

4. **Restore from Backup** (if data corrupted)
   ```bash
   # Restore latest backup
   docker-compose exec postgres psql -U mediadown \
     < /backups/postgres/backup_latest.sql
   docker-compose exec api alembic upgrade head
   ```

5. **Notify Team**
   - Post mortem in Slack
   - Log incident in issue tracker
   - Review what went wrong

---

## Sign-Off

- [ ] Project Manager: Approved for production
- [ ] DevOps Engineer: Infrastructure verified
- [ ] Backend Team Lead: Code quality verified
- [ ] Security Team: Security audit passed
- [ ] SRE/Operations: Monitoring configured and tested

---

**Deployment Date:** ________________  
**Deployed By:** ________________  
**Version/Tag:** ________________  
**Notes:** ____________________________________________________________________

