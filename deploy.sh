#!/bin/bash
#
# Production Deployment Script for AI Counselor
#
# This script automates the deployment process with:
# - Environment validation
# - Zero-downtime deployment
# - Health checks
# - Automatic rollback on failure
#
# Usage:
#   ./deploy.sh [environment]
#   environment: dev|staging|prod (default: prod)
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
ENVIRONMENT="${1:-prod}"
PROJECT_NAME="aicounselor"
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

# Validate environment
validate_environment() {
    log_info "Validating deployment environment..."

    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        log_info "Usage: ./deploy.sh [dev|staging|prod]"
        exit 1
    fi

    log_success "Environment validated: $ENVIRONMENT"
}

# Check required commands
check_dependencies() {
    log_info "Checking required dependencies..."

    local deps=("docker" "docker-compose" "git" "curl")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done

    log_success "All dependencies found"
}

# Check environment variables
check_env_vars() {
    log_info "Checking environment variables..."

    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "OPENAI_API_KEY"
        "SECRET_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
    )

    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log_info "Please set these variables in your .env.${ENVIRONMENT} file"
        exit 1
    fi

    log_success "All environment variables configured"
}

# Create backup
create_backup() {
    log_info "Creating backup of current deployment..."

    mkdir -p "$BACKUP_DIR"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/backup_${timestamp}.tar.gz"

    # Backup database
    log_info "Backing up PostgreSQL database..."
    docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U postgres aicounselor > "${BACKUP_DIR}/db_${timestamp}.sql" || true

    # Backup Redis data
    log_info "Backing up Redis data..."
    docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli --raw SAVE || true

    # Create archive
    if [[ -f "${BACKUP_DIR}/db_${timestamp}.sql" ]]; then
        tar -czf "$backup_file" -C "$BACKUP_DIR" "db_${timestamp}.sql"
        rm -f "${BACKUP_DIR}/db_${timestamp}.sql"
        log_success "Backup created: $backup_file"
        echo "$backup_file" > "${BACKUP_DIR}/latest_backup.txt"
    else
        log_warning "Database backup skipped (database not running)"
    fi
}

# Pull latest code
pull_code() {
    log_info "Pulling latest code from repository..."

    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    local current_commit=$(git rev-parse --short HEAD)

    log_info "Current branch: $current_branch"
    log_info "Current commit: $current_commit"

    git fetch origin

    if [[ "$ENVIRONMENT" == "prod" ]]; then
        git checkout main
        git pull origin main
    else
        git pull origin "$current_branch"
    fi

    local new_commit=$(git rev-parse --short HEAD)
    log_success "Code updated to commit: $new_commit"
}

# Pull Docker images
pull_images() {
    log_info "Pulling latest Docker images..."

    docker-compose -f "$COMPOSE_FILE" pull

    log_success "Docker images pulled"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    # Start database if not running
    docker-compose -f "$COMPOSE_FILE" up -d db

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10

    # Run Alembic migrations
    docker-compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head || {
        log_error "Database migration failed"
        return 1
    }

    log_success "Database migrations completed"
}

# Deploy services with zero-downtime
deploy_services() {
    log_info "Deploying services with zero-downtime strategy..."

    # Deploy backend with rolling update
    log_info "Deploying backend service..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps --scale backend=2 backend
    sleep 5
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps --scale backend=1 backend

    # Deploy frontend
    log_info "Deploying frontend service..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps frontend

    # Deploy nginx
    log_info "Deploying nginx service..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps nginx

    log_success "Services deployed"
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

# Cleanup old resources
cleanup() {
    log_info "Cleaning up old resources..."

    # Remove unused images
    docker image prune -f

    # Remove old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

    log_success "Cleanup completed"
}

# Rollback on failure
rollback_on_failure() {
    log_error "Deployment failed! Initiating rollback..."

    if [[ -f "${BACKUP_DIR}/latest_backup.txt" ]]; then
        local backup_file=$(cat "${BACKUP_DIR}/latest_backup.txt")
        if [[ -f "$backup_file" ]]; then
            log_info "Rolling back to previous version..."
            ./rollback.sh "$backup_file"
        else
            log_error "Backup file not found: $backup_file"
            log_error "Manual intervention required"
        fi
    else
        log_error "No backup found for rollback"
        log_error "Manual intervention required"
    fi
}

# Send deployment notification
send_notification() {
    local status=$1
    local message=$2

    # Webhook URL for notifications (Slack, Discord, etc.)
    if [[ -n "${WEBHOOK_URL:-}" ]]; then
        log_info "Sending deployment notification..."
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"status\": \"$status\", \"message\": \"$message\", \"environment\": \"$ENVIRONMENT\"}" \
            2>/dev/null || true
    fi
}

# Main deployment flow
main() {
    local start_time=$(date +%s)

    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║         AI Counselor - Production Deployment             ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Starting deployment to $ENVIRONMENT environment..."
    echo ""

    # Pre-deployment checks
    validate_environment
    check_dependencies

    # Load environment variables
    if [[ -f ".env.${ENVIRONMENT}" ]]; then
        log_info "Loading environment variables from .env.${ENVIRONMENT}"
        set -a
        source ".env.${ENVIRONMENT}"
        set +a
    else
        log_warning ".env.${ENVIRONMENT} not found, using current environment"
    fi

    check_env_vars

    # Create backup
    create_backup

    # Deployment steps
    if pull_code && \
       pull_images && \
       run_migrations && \
       deploy_services && \
       check_health; then

        # Success
        cleanup

        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        log_success "═══════════════════════════════════════════════════════════"
        log_success "  Deployment completed successfully in ${duration}s"
        log_success "═══════════════════════════════════════════════════════════"
        echo ""

        send_notification "success" "Deployment to $ENVIRONMENT completed successfully in ${duration}s"

        # Show service status
        log_info "Service status:"
        docker-compose -f "$COMPOSE_FILE" ps

    else
        # Failure
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        echo ""
        log_error "═══════════════════════════════════════════════════════════"
        log_error "  Deployment failed after ${duration}s"
        log_error "═══════════════════════════════════════════════════════════"
        echo ""

        send_notification "failure" "Deployment to $ENVIRONMENT failed after ${duration}s"

        rollback_on_failure
        exit 1
    fi
}

# Run main function
main "$@"
