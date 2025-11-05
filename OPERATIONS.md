# AI Counselor - Operations Guide

Complete guide for operating, monitoring, and troubleshooting the AI Counselor application in production.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deployment](#deployment)
3. [Monitoring & Logging](#monitoring--logging)
4. [Troubleshooting](#troubleshooting)
5. [Scaling](#scaling)
6. [Backup & Recovery](#backup--recovery)
7. [Security Operations](#security-operations)
8. [Performance Optimization](#performance-optimization)
9. [Maintenance](#maintenance)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Nginx (Port 80/443)                  │
│                    (Reverse Proxy + SSL)                     │
└────────────┬────────────────────────────┬────────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐   ┌──────────────────────────┐
│   Frontend (Port 3000) │   │   Backend (Port 8000)    │
│   Next.js 14           │   │   FastAPI + Python 3.11  │
└────────────────────────┘   └────────┬─────────────────┘
                                      │
                     ┌────────────────┼────────────────┐
                     ▼                ▼                ▼
            ┌────────────────┐ ┌──────────┐  ┌─────────────┐
            │ PostgreSQL 15  │ │ Redis 7  │  │  OpenAI API │
            │  + pgvector    │ │  Cache   │  │  GPT-4o-mini│
            └────────────────┘ └──────────┘  └─────────────┘
```

### Service Responsibilities

- **Nginx**: SSL termination, reverse proxy, load balancing
- **Frontend**: Next.js SSR, React UI, client-side routing
- **Backend**: REST API, WebSocket, business logic, AI processing
- **PostgreSQL**: Primary data store, vector embeddings
- **Redis**: Caching, session management, rate limiting
- **OpenAI API**: AI model inference, embeddings generation

### Data Flow

1. User → Nginx → Frontend (Static/SSR pages)
2. Frontend → Nginx → Backend API (REST/WebSocket)
3. Backend → PostgreSQL (User data, conversations)
4. Backend → Redis (Cache, sessions, rate limits)
5. Backend → OpenAI (AI completions, embeddings)

---

## Deployment

### Production Deployment

#### Automated Deployment

Use the deployment script for automated, zero-downtime deployments:

```bash
# Deploy to production
./deploy.sh prod

# Deploy to staging
./deploy.sh staging

# Deploy to development
./deploy.sh dev
```

The script performs:
1. Environment validation
2. Pre-deployment backup
3. Code pull from repository
4. Docker image updates
5. Database migrations
6. Service deployment with rolling updates
7. Health checks
8. Automatic rollback on failure

#### Manual Deployment

If automated deployment fails, use manual steps:

```bash
# 1. Load environment variables
source .env.prod

# 2. Pull latest code
git pull origin main

# 3. Build and pull images
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml pull

# 4. Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 5. Deploy services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify health
curl http://localhost:8000/health
curl http://localhost:3000
```

### Rollback Procedure

If deployment fails, rollback to previous version:

```bash
# Automatic rollback (uses latest backup)
./rollback.sh

# Manual rollback (specify backup)
./rollback.sh backups/backup_20240101_120000.tar.gz
```

The rollback script:
1. Stops current services
2. Restores database from backup
3. Checks out previous git commit
4. Rebuilds and restarts services
5. Clears Redis cache
6. Runs health checks

### Environment Configuration

#### Required Environment Variables

Create `.env.prod` with:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:STRONG_PASSWORD@db:5432/aicounselor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=STRONG_PASSWORD
POSTGRES_DB=aicounselor

# Redis
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=STRONG_PASSWORD

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key

# Security
SECRET_KEY=your-secret-key-min-32-chars
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Application
ENVIRONMENT=production
BACKEND_URL=https://api.yourdomain.com
FRONTEND_URL=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Monitoring (optional)
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### Generate Secure Secrets

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 24
```

---

## Monitoring & Logging

### Health Checks

#### Backend Health Check

```bash
# Local
curl http://localhost:8000/health

# Production
curl https://api.yourdomain.com/health

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### Frontend Health Check

```bash
# Local
curl http://localhost:3000

# Production
curl https://yourdomain.com

# Should return 200 OK with HTML
```

#### Service Status

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check specific service
docker-compose -f docker-compose.prod.yml ps backend

# View resource usage
docker stats
```

### Logging

#### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# Filter by time
docker-compose -f docker-compose.prod.yml logs --since=1h backend
```

#### Log Locations

- **Backend logs**: `./backend/logs/`
- **Nginx logs**: `./nginx/logs/`
- **Docker logs**: `/var/lib/docker/containers/`

#### Log Rotation

Logs are automatically rotated by Docker:
- Max size: 10MB per file
- Max files: 3 files per service
- Total: ~30MB per service

### Metrics to Monitor

#### System Metrics

- **CPU Usage**: Should be < 80% average
- **Memory Usage**: Should be < 80% average
- **Disk Usage**: Should be < 80% total
- **Network I/O**: Monitor for anomalies

```bash
# CPU and memory
docker stats --no-stream

# Disk usage
df -h

# Network connections
netstat -an | grep :8000 | wc -l
```

#### Application Metrics

- **Request Rate**: Requests per second
- **Response Time**: p50, p95, p99 latencies
- **Error Rate**: 4xx and 5xx responses
- **Cache Hit Rate**: Should be > 60%

```bash
# Request rate (from nginx logs)
tail -1000 nginx/logs/access.log | wc -l

# Error rate
docker-compose -f docker-compose.prod.yml logs backend | grep ERROR | wc -l

# Cache hit rate (Redis)
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO stats | grep keyspace
```

#### Database Metrics

```bash
# Connection count
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('aicounselor'));"

# Slow queries
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d aicounselor -c \
  "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Setting Up Monitoring Dashboard

#### Prometheus + Grafana (Recommended)

1. **Install Prometheus**:

```yaml
# Add to docker-compose.prod.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
```

2. **Install Grafana**:

```yaml
grafana:
  image: grafana/grafana:latest
  volumes:
    - grafana_data:/var/lib/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

3. **Configure Prometheus** (`monitoring/prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

#### Simple Monitoring Script

Create `monitoring/monitor.sh`:

```bash
#!/bin/bash
# Simple monitoring script

while true; do
  echo "=== $(date) ==="

  # Backend health
  curl -s http://localhost:8000/health | jq .

  # Service status
  docker-compose -f docker-compose.prod.yml ps --format json | jq .

  # Resource usage
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

  echo ""
  sleep 60
done
```

### Alerts Configuration

#### Webhook Alerts (Slack/Discord)

Set `WEBHOOK_URL` in `.env.prod`:

```bash
# Slack webhook
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Discord webhook
WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
```

Deploy and rollback scripts will automatically send notifications.

#### Email Alerts

Install and configure `mailutils`:

```bash
# Install
apt-get install mailutils

# Send test email
echo "Test alert" | mail -s "AI Counselor Alert" admin@yourdomain.com
```

Add to monitoring script:

```bash
# Check if backend is down
if ! curl -f -s http://localhost:8000/health > /dev/null; then
  echo "Backend is down!" | mail -s "ALERT: Backend Down" admin@yourdomain.com
fi
```

---

## Troubleshooting

### Common Issues

#### 1. Backend Not Starting

**Symptoms**: Backend container exits immediately

**Diagnosis**:
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check last 50 lines
docker-compose -f docker-compose.prod.yml logs --tail=50 backend
```

**Common Causes**:

a) **Database connection failure**:
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Test connection
docker-compose -f docker-compose.prod.yml exec backend \
  python -c "import asyncio; from app.core.database import test_connection; asyncio.run(test_connection())"
```

b) **Missing environment variables**:
```bash
# Check env vars
docker-compose -f docker-compose.prod.yml exec backend env | grep -E "DATABASE_URL|REDIS_URL|OPENAI_API_KEY|SECRET_KEY"
```

c) **Port already in use**:
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

**Solution**:
```bash
# Restart with fresh state
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. Frontend Not Loading

**Symptoms**: 502 Bad Gateway or blank page

**Diagnosis**:
```bash
# Check frontend logs
docker-compose -f docker-compose.prod.yml logs frontend

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```

**Common Causes**:

a) **Build failure**:
```bash
# Rebuild frontend
docker-compose -f docker-compose.prod.yml build --no-cache frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

b) **API connection issue**:
```bash
# Check NEXT_PUBLIC_API_URL
docker-compose -f docker-compose.prod.yml exec frontend env | grep NEXT_PUBLIC_API_URL
```

c) **Nginx misconfiguration**:
```bash
# Test nginx config
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

#### 3. Database Connection Errors

**Symptoms**: "could not connect to server" or "password authentication failed"

**Diagnosis**:
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Check database logs
docker-compose -f docker-compose.prod.yml logs db
```

**Solutions**:

a) **Database not ready**:
```bash
# Wait for database
docker-compose -f docker-compose.prod.yml up -d db
sleep 30
docker-compose -f docker-compose.prod.yml restart backend
```

b) **Wrong credentials**:
```bash
# Verify DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql+asyncpg://postgres:PASSWORD@db:5432/aicounselor

# Test connection
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d aicounselor -c "SELECT 1;"
```

c) **Database corruption**:
```bash
# Restore from backup
./rollback.sh
```

#### 4. Redis Connection Errors

**Symptoms**: "Connection refused" or "NOAUTH Authentication required"

**Diagnosis**:
```bash
# Check Redis is running
docker-compose -f docker-compose.prod.yml ps redis

# Test connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
```

**Solutions**:

a) **Redis not running**:
```bash
docker-compose -f docker-compose.prod.yml up -d redis
```

b) **Wrong password**:
```bash
# Test with password
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" ping
```

c) **Cache corruption**:
```bash
# Flush all cache
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a "$REDIS_PASSWORD" FLUSHALL
```

#### 5. High Memory Usage

**Symptoms**: OOM kills, slow performance

**Diagnosis**:
```bash
# Check memory usage
docker stats --no-stream

# Check system memory
free -h

# Check which process is using memory
docker-compose -f docker-compose.prod.yml exec backend \
  ps aux --sort=-%mem | head -10
```

**Solutions**:

a) **Increase container limits**:
```yaml
# In docker-compose.prod.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G  # Increase from 2G
```

b) **Clear Redis cache**:
```bash
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" FLUSHALL
```

c) **Restart services**:
```bash
docker-compose -f docker-compose.prod.yml restart
```

#### 6. Slow API Response

**Symptoms**: API takes > 5 seconds to respond

**Diagnosis**:
```bash
# Check response time
time curl http://localhost:8000/health

# Check database connections
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Check slow queries
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d aicounselor -c \
  "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"
```

**Solutions**:

a) **Add database indexes**:
```sql
-- Connect to database
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -d aicounselor

-- Create indexes
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
```

b) **Check cache hit rate**:
```bash
# Check Redis stats
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" INFO stats
```

c) **Scale backend**:
```bash
# Run multiple backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

#### 7. SSL/HTTPS Issues

**Symptoms**: "Connection not secure" or certificate errors

**Solutions**:

a) **Generate SSL certificates** (Let's Encrypt):
```bash
# Install certbot
apt-get install certbot python3-certbot-nginx

# Generate certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

b) **Update nginx configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
}
```

---

## Scaling

### Horizontal Scaling

#### Scale Backend Services

```bash
# Scale to 3 backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Verify
docker-compose -f docker-compose.prod.yml ps backend
```

#### Load Balancing (Nginx)

Update `nginx/nginx.prod.conf`:

```nginx
upstream backend {
    least_conn;  # Load balancing method
    server backend:8000 max_fails=3 fail_timeout=30s;
    server backend:8000 max_fails=3 fail_timeout=30s;
    server backend:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /api {
        proxy_pass http://backend;
    }
}
```

### Vertical Scaling

#### Increase Container Resources

Edit `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'      # Increase from 2
          memory: 4G     # Increase from 2G
        reservations:
          cpus: '1'
          memory: 1G
```

Apply changes:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Database Scaling

#### Read Replicas

1. **Add read replica**:

```yaml
# In docker-compose.prod.yml
db-replica:
  image: pgvector/pgvector:pg15
  environment:
    - PGUSER=replicator
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  command: postgres -c 'max_wal_senders=3' -c 'wal_level=replica'
```

2. **Configure connection pooling** (PgBouncer):

```yaml
pgbouncer:
  image: pgbouncer/pgbouncer:latest
  environment:
    - DB_HOST=db
    - DB_USER=postgres
    - DB_PASSWORD=${POSTGRES_PASSWORD}
  ports:
    - "6432:6432"
```

#### Database Optimization

```sql
-- Vacuum database
VACUUM ANALYZE;

-- Reindex
REINDEX DATABASE aicounselor;

-- Update statistics
ANALYZE;
```

### Redis Scaling

#### Redis Cluster

For high availability:

```yaml
redis-cluster:
  image: redis:7-alpine
  command: redis-cli --cluster create redis1:6379 redis2:6379 redis3:6379
```

#### Redis Sentinel

For automatic failover:

```yaml
redis-sentinel:
  image: redis:7-alpine
  command: redis-sentinel /etc/sentinel.conf
```

---

## Backup & Recovery

### Automated Backups

#### Daily Database Backup

Create `scripts/backup-db.sh`:

```bash
#!/bin/bash
# Daily database backup

BACKUP_DIR="/backups/daily"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_$DATE.sql"

mkdir -p "$BACKUP_DIR"

# Backup database
docker-compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U postgres aicounselor > "$BACKUP_FILE"

# Compress
gzip "$BACKUP_FILE"

# Keep only last 7 days
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

#### Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/aicounselor/scripts/backup-db.sh >> /var/log/backup.log 2>&1
```

### Manual Backups

#### Full Backup

```bash
# Database
docker-compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U postgres aicounselor > backup_$(date +%Y%m%d).sql

# Redis
docker-compose -f docker-compose.prod.yml exec -T redis \
  redis-cli -a "$REDIS_PASSWORD" --rdb dump.rdb

# Application files
tar -czf backup_files_$(date +%Y%m%d).tar.gz \
  backend/ frontend/ nginx/ docker-compose.prod.yml .env.prod
```

### Recovery Procedures

#### Restore Database

```bash
# Stop backend
docker-compose -f docker-compose.prod.yml stop backend

# Restore from backup
docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres -d aicounselor < backup_20240101.sql

# Restart backend
docker-compose -f docker-compose.prod.yml start backend
```

#### Restore Redis

```bash
# Stop Redis
docker-compose -f docker-compose.prod.yml stop redis

# Copy dump file
docker cp dump.rdb aicounselor-redis-1:/data/dump.rdb

# Start Redis
docker-compose -f docker-compose.prod.yml start redis
```

#### Disaster Recovery

Full system recovery:

```bash
# 1. Restore application files
tar -xzf backup_files_20240101.tar.gz

# 2. Restore environment
cp .env.prod.backup .env.prod

# 3. Start services
docker-compose -f docker-compose.prod.yml up -d db redis

# 4. Restore database
docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres -d aicounselor < backup_20240101.sql

# 5. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 6. Verify
curl http://localhost:8000/health
```

### Backup to Cloud Storage

#### AWS S3

```bash
# Install AWS CLI
apt-get install awscli

# Configure credentials
aws configure

# Upload backup
aws s3 cp backup_20240101.sql.gz s3://your-bucket/backups/

# Download backup
aws s3 cp s3://your-bucket/backups/backup_20240101.sql.gz .
```

#### Google Cloud Storage

```bash
# Install gsutil
curl https://sdk.cloud.google.com | bash

# Upload backup
gsutil cp backup_20240101.sql.gz gs://your-bucket/backups/

# Download backup
gsutil cp gs://your-bucket/backups/backup_20240101.sql.gz .
```

---

## Security Operations

### Security Checklist

- [ ] All environment variables use strong passwords
- [ ] SSL/TLS certificates are valid and auto-renewing
- [ ] Firewall rules allow only necessary ports
- [ ] Database access restricted to localhost
- [ ] Redis password authentication enabled
- [ ] Security headers configured in nginx
- [ ] Rate limiting enabled
- [ ] Regular security updates applied
- [ ] Audit logging enabled
- [ ] Backups encrypted

### Rotate Secrets

#### Rotate Database Password

```bash
# 1. Generate new password
NEW_PASSWORD=$(openssl rand -base64 32)

# 2. Update in database
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "ALTER USER postgres PASSWORD '$NEW_PASSWORD';"

# 3. Update .env.prod
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PASSWORD/" .env.prod

# 4. Update DATABASE_URL
# Edit .env.prod manually

# 5. Restart services
docker-compose -f docker-compose.prod.yml restart
```

#### Rotate SECRET_KEY

```bash
# 1. Generate new key
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update .env.prod
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET/" .env.prod

# 3. Restart backend
docker-compose -f docker-compose.prod.yml restart backend

# Note: This will invalidate all existing JWT tokens
```

### Security Monitoring

#### Check Failed Login Attempts

```bash
# View audit logs
docker-compose -f docker-compose.prod.yml logs backend | grep "Invalid credentials"

# Count failed attempts per IP
docker-compose -f docker-compose.prod.yml logs backend | \
  grep "Invalid credentials" | \
  awk '{print $NF}' | \
  sort | uniq -c | sort -rn
```

#### Monitor Rate Limiting

```bash
# Check rate limit violations
docker-compose -f docker-compose.prod.yml logs backend | grep "Rate limit exceeded"

# Most rate-limited IPs
docker-compose -f docker-compose.prod.yml logs backend | \
  grep "Rate limit" | \
  awk '{print $NF}' | \
  sort | uniq -c | sort -rn
```

### Update Dependencies

#### Update Python Dependencies

```bash
# Check for updates
docker-compose -f docker-compose.prod.yml exec backend \
  pip list --outdated

# Update requirements.txt
# Edit backend/requirements.txt

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d backend
```

#### Update Node Dependencies

```bash
# Check for updates
docker-compose -f docker-compose.prod.yml exec frontend \
  npm outdated

# Update package.json
# Edit frontend/package.json

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

---

## Performance Optimization

### Database Optimization

#### Analyze Query Performance

```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries
SELECT
  calls,
  total_time,
  mean_time,
  query
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

#### Add Indexes

```sql
-- User queries
CREATE INDEX idx_users_email_hash ON users(email_hash);
CREATE INDEX idx_users_session_token ON users(session_token);

-- Conversation queries
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- Message queries
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);

-- Vector search
CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops);
```

### Cache Optimization

#### Monitor Cache Performance

```bash
# Cache hit rate
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" INFO stats | grep keyspace

# Memory usage
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli -a "$REDIS_PASSWORD" INFO memory
```

#### Optimize Cache Strategy

```python
# Increase semantic cache TTL for common queries
SEMANTIC_CACHE_TTL = 3600  # 1 hour for high-hit queries

# Reduce TTL for rare queries
RARE_QUERY_TTL = 300  # 5 minutes
```

### API Optimization

#### Enable Compression

In `nginx/nginx.prod.conf`:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;
```

#### HTTP/2

```nginx
server {
    listen 443 ssl http2;  # Enable HTTP/2
    # ...
}
```

#### CDN Integration

Use Cloudflare or AWS CloudFront for static assets:

```javascript
// In frontend next.config.js
module.exports = {
  assetPrefix: process.env.CDN_URL || '',
}
```

---

## Maintenance

### Regular Maintenance Tasks

#### Daily

- [ ] Check service health
- [ ] Review error logs
- [ ] Monitor disk space

```bash
# Daily health check script
curl -f http://localhost:8000/health || echo "Backend DOWN!"
curl -f http://localhost:3000 || echo "Frontend DOWN!"
df -h | grep -E "9[0-9]%|100%" && echo "Disk space critical!"
```

#### Weekly

- [ ] Review performance metrics
- [ ] Check database size
- [ ] Verify backups

```bash
# Weekly maintenance script
docker-compose -f docker-compose.prod.yml exec db \
  psql -U postgres -c "SELECT pg_size_pretty(pg_database_size('aicounselor'));"

ls -lh backups/ | tail -7
```

#### Monthly

- [ ] Update dependencies
- [ ] Rotate logs
- [ ] Review security policies
- [ ] Test disaster recovery

```bash
# Monthly security audit
docker-compose -f docker-compose.prod.yml exec backend pip list --outdated
docker-compose -f docker-compose.prod.yml exec frontend npm outdated
```

### Scheduled Downtime

Plan maintenance windows:

```bash
# 1. Notify users (via application banner or email)

# 2. Create backup
./deploy.sh prod  # This creates automatic backup

# 3. Perform maintenance
docker-compose -f docker-compose.prod.yml down
# ... perform maintenance ...
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify
curl http://localhost:8000/health
```

---

## Emergency Contacts

### Escalation Path

1. **On-call Engineer**: DevOps team
2. **Senior Engineer**: Backend/Frontend leads
3. **CTO/VP Engineering**: Critical outages only

### External Services

- **OpenAI Support**: https://help.openai.com/
- **AWS Support**: https://console.aws.amazon.com/support/
- **Hosting Provider**: Contact your cloud provider

### Incident Response

1. **Detect**: Monitoring alerts or user reports
2. **Assess**: Determine severity (P0-P4)
3. **Respond**: Follow troubleshooting guide
4. **Communicate**: Update status page
5. **Resolve**: Fix issue and verify
6. **Document**: Create postmortem

---

## Appendix

### Useful Commands

```bash
# Quick restart all services
docker-compose -f docker-compose.prod.yml restart

# Rebuild specific service
docker-compose -f docker-compose.prod.yml build --no-cache backend

# View real-time logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100

# Execute command in container
docker-compose -f docker-compose.prod.yml exec backend bash

# Clean up everything
docker-compose -f docker-compose.prod.yml down -v --remove-orphans
docker system prune -af --volumes

# Export database
docker-compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U postgres aicounselor | gzip > backup.sql.gz

# Import database
gunzip < backup.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U postgres -d aicounselor
```

### Configuration Files

- **Docker Compose**: `docker-compose.prod.yml`
- **Nginx**: `nginx/nginx.prod.conf`
- **Environment**: `.env.prod`
- **Database**: `database/init/`
- **Redis**: `redis/redis.prod.conf`

### Documentation Links

- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js**: https://nextjs.org/docs
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/documentation
- **Docker**: https://docs.docker.com/

---

**Last Updated**: 2024-01-01
**Version**: 1.0
**Maintainer**: DevOps Team
