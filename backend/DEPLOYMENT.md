# Deployment Guide - Mindful AI Counselor Backend

This guide covers deployment options for the Mindful AI Counselor backend service.

## Table of Contents

- [Quick Start with Docker](#quick-start-with-docker)
- [Manual Deployment](#manual-deployment)
- [Database Migrations](#database-migrations)
- [Environment Configuration](#environment-configuration)
- [Health Checks](#health-checks)
- [Production Considerations](#production-considerations)

## Quick Start with Docker

The easiest way to deploy the entire stack is using Docker Compose.

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- OpenAI API key

### Step 1: Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key and other settings
nano .env
```

**Required environment variables:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`

### Step 2: Start Services

```bash
# Start all services (PostgreSQL, Redis, Backend)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check service status
docker-compose ps
```

### Step 3: Run Database Migrations

```bash
# Run migrations inside the backend container
docker-compose exec backend alembic upgrade head

# Verify migration
docker-compose exec backend alembic current
```

### Step 4: Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Manual Deployment

For production environments without Docker, follow these steps.

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- Redis 7+

### Step 1: Install PostgreSQL with pgvector

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-14 postgresql-contrib
sudo apt-get install postgresql-14-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE aicounselor;"
sudo -u postgres psql -c "CREATE USER aicounselor WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE aicounselor TO aicounselor;"

# Enable pgvector extension
sudo -u postgres psql -d aicounselor -c "CREATE EXTENSION vector;"
```

### Step 2: Install Redis

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Step 3: Install Backend

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your configuration
```

### Step 4: Run Migrations

```bash
# Ensure .env is configured with correct DATABASE_URL
alembic upgrade head
```

### Step 5: Start Backend

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production with Gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Step 6: Setup Systemd Service (Optional)

Create `/etc/systemd/system/aicounselor.service`:

```ini
[Unit]
Description=Mindful AI Counselor Backend
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/aicounselor/backend
Environment="PATH=/opt/aicounselor/backend/venv/bin"
ExecStart=/opt/aicounselor/backend/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aicounselor
sudo systemctl start aicounselor
sudo systemctl status aicounselor
```

## Database Migrations

### Create New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review generated migration in alembic/versions/
# Edit if necessary

# Apply migration
alembic upgrade head
```

### Migration Commands

```bash
# View current version
alembic current

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Generated with `openssl rand -hex 32` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional Variables

See `.env.example` for complete list of configuration options.

## Health Checks

### Endpoints

- **GET /health** - Basic health check
- **GET /health/detailed** - Detailed service status (DB, Redis, OpenAI)

### Monitoring

```bash
# Docker health status
docker-compose ps

# Backend logs
docker-compose logs -f backend

# Database logs
docker-compose logs -f postgres

# Redis logs
docker-compose logs -f redis
```

## Production Considerations

### Security

1. **Use strong SECRET_KEY**
   ```bash
   openssl rand -hex 32
   ```

2. **Enable HTTPS**
   - Use reverse proxy (Nginx, Caddy)
   - Configure SSL certificates
   - Update `ALLOWED_ORIGINS` in .env

3. **Database Security**
   - Use strong passwords
   - Restrict network access
   - Enable SSL connections
   - Regular backups

4. **API Rate Limiting**
   - Configure `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR`
   - Monitor Redis for rate limit keys

### Performance

1. **Database Optimization**
   - Configure PostgreSQL connection pooling
   - Enable query caching
   - Regular VACUUM operations
   - Monitor slow queries

2. **Redis Configuration**
   - Configure maxmemory policy
   - Enable persistence (AOF)
   - Monitor memory usage

3. **Backend Scaling**
   - Run multiple workers
   - Use load balancer
   - Monitor memory and CPU usage

### Backups

```bash
# PostgreSQL backup
docker-compose exec postgres pg_dump -U postgres aicounselor > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres aicounselor < backup.sql

# Redis backup
docker-compose exec redis redis-cli SAVE
```

### Monitoring & Logging

1. **Application Logs**
   - Configure `LOG_LEVEL` in .env
   - Optional: Setup Sentry with `SENTRY_DSN`

2. **Metrics**
   - Monitor API response times
   - Track OpenAI API usage
   - Monitor database query performance
   - Track Redis cache hit rates

3. **Alerts**
   - Configure crisis detection alerts with `CRISIS_ALERT_EMAIL`
   - Setup uptime monitoring
   - Configure resource usage alerts

### Compliance

1. **HIPAA Compliance**
   - Enable encryption: `ENABLE_ENCRYPTION=true`
   - Enable audit logging: `ENABLE_AUDIT_LOG=true`
   - Configure data retention: `DATA_RETENTION_DAYS=90`
   - Use SSL/TLS for all connections
   - Implement access controls
   - Regular security audits

2. **GDPR Compliance**
   - Data export API available at `/api/v1/export/all-data`
   - Soft delete with `is_deleted` flag
   - Anonymous user support
   - Consent tracking in user model

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection from backend
docker-compose exec backend python -c "from app.core.database import engine; import asyncio; asyncio.run(engine.connect())"

# View PostgreSQL logs
docker-compose logs postgres
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis
```

### Migration Issues

```bash
# Check current migration status
alembic current

# View migration history
alembic history --verbose

# Manually inspect database
docker-compose exec postgres psql -U postgres aicounselor -c "\dt"
```

### OpenAI API Issues

```bash
# Verify API key is set
docker-compose exec backend python -c "import os; print('Key set:', bool(os.getenv('OPENAI_API_KEY')))"

# Test OpenAI connection
docker-compose exec backend python -c "from openai import OpenAI; client = OpenAI(); print(client.models.list())"
```

## Support

For issues or questions:
- Check the [API Documentation](http://localhost:8000/docs)
- Review application logs
- Open an issue on GitHub
