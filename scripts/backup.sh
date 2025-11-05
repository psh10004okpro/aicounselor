#!/bin/bash
#
# Automated Backup Script for AI Counselor
#
# Creates backups of:
# - PostgreSQL database
# - Redis data
# - Application files
# - Configuration files
#
# Usage:
#   ./scripts/backup.sh [daily|weekly|monthly]
#

set -e

# Configuration
BACKUP_TYPE="${1:-daily}"
BACKUP_BASE_DIR="./backups"
BACKUP_DIR="${BACKUP_BASE_DIR}/${BACKUP_TYPE}"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE="docker-compose.prod.yml"

# Retention periods (in days)
DAILY_RETENTION=7
WEEKLY_RETENTION=30
MONTHLY_RETENTION=365

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ✓ $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log_info "Starting $BACKUP_TYPE backup..."

# 1. Backup PostgreSQL database
log_info "Backing up PostgreSQL database..."
DB_BACKUP_FILE="${BACKUP_DIR}/db_${DATE}.sql"

docker-compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U postgres aicounselor > "$DB_BACKUP_FILE"

# Compress database backup
gzip "$DB_BACKUP_FILE"
log_success "Database backup: ${DB_BACKUP_FILE}.gz"

# 2. Backup Redis data
log_info "Backing up Redis data..."
REDIS_BACKUP_FILE="${BACKUP_DIR}/redis_${DATE}.rdb"

# Trigger Redis save
docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli --raw SAVE 2>/dev/null || true

# Copy Redis dump
docker cp $(docker-compose -f "$COMPOSE_FILE" ps -q redis):/data/dump.rdb "$REDIS_BACKUP_FILE" 2>/dev/null || true

if [[ -f "$REDIS_BACKUP_FILE" ]]; then
    gzip "$REDIS_BACKUP_FILE"
    log_success "Redis backup: ${REDIS_BACKUP_FILE}.gz"
else
    log_info "Redis backup skipped (no data)"
fi

# 3. Backup application files (for full backups only)
if [[ "$BACKUP_TYPE" == "weekly" ]] || [[ "$BACKUP_TYPE" == "monthly" ]]; then
    log_info "Backing up application files..."
    APP_BACKUP_FILE="${BACKUP_DIR}/app_${DATE}.tar.gz"

    tar -czf "$APP_BACKUP_FILE" \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='backups' \
        backend/ frontend/ nginx/ docker-compose.prod.yml .env.prod 2>/dev/null || true

    log_success "Application backup: $APP_BACKUP_FILE"
fi

# 4. Create backup manifest
MANIFEST_FILE="${BACKUP_DIR}/manifest_${DATE}.txt"
cat > "$MANIFEST_FILE" << EOF
AI Counselor Backup Manifest
============================
Type: $BACKUP_TYPE
Date: $(date)
Hostname: $(hostname)

Files:
EOF

ls -lh "${BACKUP_DIR}"/*_${DATE}* >> "$MANIFEST_FILE"

# 5. Calculate checksums
log_info "Calculating checksums..."
CHECKSUM_FILE="${BACKUP_DIR}/checksums_${DATE}.sha256"
sha256sum "${BACKUP_DIR}"/*_${DATE}*.gz > "$CHECKSUM_FILE" 2>/dev/null || true
log_success "Checksums: $CHECKSUM_FILE"

# 6. Create consolidated archive
log_info "Creating consolidated backup archive..."
ARCHIVE_FILE="${BACKUP_BASE_DIR}/backup_${BACKUP_TYPE}_${DATE}.tar.gz"

tar -czf "$ARCHIVE_FILE" -C "$BACKUP_DIR" . 2>/dev/null

ARCHIVE_SIZE=$(du -h "$ARCHIVE_FILE" | cut -f1)
log_success "Archive created: $ARCHIVE_FILE ($ARCHIVE_SIZE)"

# 7. Update latest backup pointer
echo "$ARCHIVE_FILE" > "${BACKUP_BASE_DIR}/latest_${BACKUP_TYPE}_backup.txt"

# 8. Cleanup old backups based on retention
log_info "Cleaning up old backups..."

case $BACKUP_TYPE in
    daily)
        find "$BACKUP_DIR" -name "*.gz" -mtime +$DAILY_RETENTION -delete
        find "$BACKUP_BASE_DIR" -name "backup_daily_*.tar.gz" -mtime +$DAILY_RETENTION -delete
        ;;
    weekly)
        find "$BACKUP_DIR" -name "*.gz" -mtime +$WEEKLY_RETENTION -delete
        find "$BACKUP_BASE_DIR" -name "backup_weekly_*.tar.gz" -mtime +$WEEKLY_RETENTION -delete
        ;;
    monthly)
        find "$BACKUP_DIR" -name "*.gz" -mtime +$MONTHLY_RETENTION -delete
        find "$BACKUP_BASE_DIR" -name "backup_monthly_*.tar.gz" -mtime +$MONTHLY_RETENTION -delete
        ;;
esac

log_success "Old backups cleaned up"

# 9. Upload to cloud storage (if configured)
if [[ -n "${AWS_S3_BUCKET:-}" ]]; then
    log_info "Uploading to AWS S3..."
    aws s3 cp "$ARCHIVE_FILE" "s3://${AWS_S3_BUCKET}/backups/" || log_info "S3 upload failed"
fi

if [[ -n "${GCS_BUCKET:-}" ]]; then
    log_info "Uploading to Google Cloud Storage..."
    gsutil cp "$ARCHIVE_FILE" "gs://${GCS_BUCKET}/backups/" || log_info "GCS upload failed"
fi

# 10. Send notification
if [[ -n "${WEBHOOK_URL:-}" ]]; then
    curl -X POST "$WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{
            \"type\": \"backup\",
            \"backup_type\": \"$BACKUP_TYPE\",
            \"status\": \"success\",
            \"archive\": \"$ARCHIVE_FILE\",
            \"size\": \"$ARCHIVE_SIZE\",
            \"timestamp\": \"$(date -Iseconds)\"
        }" \
        2>/dev/null || true
fi

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              Backup Completed Successfully                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
log_success "Backup type: $BACKUP_TYPE"
log_success "Archive: $ARCHIVE_FILE"
log_success "Size: $ARCHIVE_SIZE"
echo ""

# List recent backups
log_info "Recent backups:"
ls -lht "${BACKUP_BASE_DIR}"/backup_*.tar.gz | head -5
