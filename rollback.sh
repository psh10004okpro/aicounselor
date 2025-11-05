#!/bin/bash
#
# Rollback Script for AI Counselor
#
# This script handles rollback to a previous deployment:
# - Service rollback
# - Database restoration
# - Health verification
#
# Usage:
#   ./rollback.sh [backup_file]
#   ./rollback.sh                    # Rollback to latest backup
#   ./rollback.sh backups/backup_20240101_120000.tar.gz
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
COMPOSE_FILE="docker-compose.prod.yml"
MAX_HEALTH_CHECK_ATTEMPTS=30
HEALTH_CHECK_INTERVAL=5

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get backup file
get_backup_file() {
    local backup_file="${1:-}"

    if [[ -z "$backup_file" ]]; then
        # Use latest backup
        if [[ -f "${BACKUP_DIR}/latest_backup.txt" ]]; then
            backup_file=$(cat "${BACKUP_DIR}/latest_backup.txt")
        else
            log_error "No backup specified and no latest backup found"
            log_info "Usage: ./rollback.sh [backup_file]"
            exit 1
        fi
    fi

    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    echo "$backup_file"
}

# Confirm rollback
confirm_rollback() {
    local backup_file=$1

    echo ""
    log_warning "╔═══════════════════════════════════════════════════════════╗"
    log_warning "║                  ROLLBACK CONFIRMATION                    ║"
    log_warning "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    log_warning "You are about to rollback to:"
    log_warning "  Backup: $(basename "$backup_file")"
    echo ""
    log_warning "This will:"
    log_warning "  1. Stop current services"
    log_warning "  2. Restore database from backup"
    log_warning "  3. Rollback to previous git commit"
    log_warning "  4. Restart services"
    echo ""

    read -p "Are you sure you want to continue? (yes/no): " -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

# Stop services
stop_services() {
    log_info "Stopping current services..."

    docker-compose -f "$COMPOSE_FILE" stop backend frontend nginx

    log_success "Services stopped"
}

# Restore database
restore_database() {
    local backup_file=$1

    log_info "Restoring database from backup..."

    # Extract backup
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"

    # Find SQL dump
    local sql_file=$(find "$temp_dir" -name "db_*.sql" | head -n 1)

    if [[ -z "$sql_file" ]]; then
        log_error "No database dump found in backup"
        rm -rf "$temp_dir"
        return 1
    fi

    # Ensure database is running
    docker-compose -f "$COMPOSE_FILE" up -d db
    sleep 10

    # Drop and recreate database
    log_info "Recreating database..."
    docker-compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS aicounselor;"
    docker-compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -c "CREATE DATABASE aicounselor;"

    # Restore from dump
    log_info "Restoring from dump..."
    docker-compose -f "$COMPOSE_FILE" exec -T db psql -U postgres -d aicounselor < "$sql_file"

    # Cleanup
    rm -rf "$temp_dir"

    log_success "Database restored successfully"
}

# Rollback git commit
rollback_git() {
    log_info "Rolling back git commit..."

    # Get previous commit
    local current_commit=$(git rev-parse HEAD)
    local previous_commit=$(git rev-parse HEAD~1)

    log_info "Current commit: $current_commit"
    log_info "Rolling back to: $previous_commit"

    # Checkout previous commit
    git checkout "$previous_commit"

    log_success "Git rolled back to: $previous_commit"
}

# Rebuild and restart services
restart_services() {
    log_info "Rebuilding and restarting services..."

    # Rebuild images
    docker-compose -f "$COMPOSE_FILE" build

    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d

    log_success "Services restarted"
}

# Health check
check_health() {
    log_info "Running health checks..."

    local backend_url="${BACKEND_URL:-http://localhost:8000}"
    local frontend_url="${FRONTEND_URL:-http://localhost:3000}"

    # Check backend health
    log_info "Checking backend health at ${backend_url}/health..."
    for i in $(seq 1 $MAX_HEALTH_CHECK_ATTEMPTS); do
        if curl -f -s "${backend_url}/health" > /dev/null; then
            log_success "Backend is healthy"
            break
        else
            if [[ $i -eq $MAX_HEALTH_CHECK_ATTEMPTS ]]; then
                log_error "Backend health check failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts"
                return 1
            fi
            log_info "Attempt $i/$MAX_HEALTH_CHECK_ATTEMPTS failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
            sleep $HEALTH_CHECK_INTERVAL
        fi
    done

    # Check frontend health
    log_info "Checking frontend health at ${frontend_url}..."
    for i in $(seq 1 $MAX_HEALTH_CHECK_ATTEMPTS); do
        if curl -f -s "$frontend_url" > /dev/null; then
            log_success "Frontend is healthy"
            break
        else
            if [[ $i -eq $MAX_HEALTH_CHECK_ATTEMPTS ]]; then
                log_error "Frontend health check failed after $MAX_HEALTH_CHECK_ATTEMPTS attempts"
                return 1
            fi
            log_info "Attempt $i/$MAX_HEALTH_CHECK_ATTEMPTS failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
            sleep $HEALTH_CHECK_INTERVAL
        fi
    done

    log_success "All health checks passed"
}

# Clear Redis cache
clear_cache() {
    log_info "Clearing Redis cache..."

    docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli FLUSHALL || true

    log_success "Cache cleared"
}

# Send notification
send_notification() {
    local status=$1
    local message=$2

    # Webhook URL for notifications
    if [[ -n "${WEBHOOK_URL:-}" ]]; then
        log_info "Sending rollback notification..."
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"status\": \"$status\", \"message\": \"$message\", \"type\": \"rollback\"}" \
            2>/dev/null || true
    fi
}

# Main rollback flow
main() {
    local start_time=$(date +%s)

    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║          AI Counselor - Rollback Procedure                ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    # Get backup file
    local backup_file=$(get_backup_file "${1:-}")
    log_info "Using backup: $(basename "$backup_file")"

    # Confirm rollback
    if [[ "${SKIP_CONFIRMATION:-false}" != "true" ]]; then
        confirm_rollback "$backup_file"
    fi

    log_info "Starting rollback procedure..."
    echo ""

    # Rollback steps
    if stop_services && \
       restore_database "$backup_file" && \
       rollback_git && \
       restart_services && \
       clear_cache && \
       check_health; then

        # Success
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        log_success "═══════════════════════════════════════════════════════════"
        log_success "  Rollback completed successfully in ${duration}s"
        log_success "═══════════════════════════════════════════════════════════"
        echo ""

        send_notification "success" "Rollback completed successfully in ${duration}s"

        # Show service status
        log_info "Service status:"
        docker-compose -f "$COMPOSE_FILE" ps

    else
        # Failure
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        log_error "═══════════════════════════════════════════════════════════"
        log_error "  Rollback failed after ${duration}s"
        log_error "═══════════════════════════════════════════════════════════"
        echo ""
        log_error "Manual intervention required!"
        log_error "Please check service logs: docker-compose -f $COMPOSE_FILE logs"

        send_notification "failure" "Rollback failed after ${duration}s - manual intervention required"

        exit 1
    fi
}

# Run main function
main "$@"
