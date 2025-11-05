#!/bin/bash
#
# Simple Monitoring Script for AI Counselor
#
# Monitors service health, resource usage, and sends alerts
#
# Usage:
#   ./scripts/monitor.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
CHECK_INTERVAL=60  # Check every 60 seconds
ALERT_EMAIL="${ALERT_EMAIL:-}"
WEBHOOK_URL="${WEBHOOK_URL:-}"

# Logging
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ✓ $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ⚠ $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ✗ $1"
}

# Send alert
send_alert() {
    local severity=$1
    local message=$2

    # Webhook notification
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"severity\": \"$severity\",
                \"message\": \"$message\",
                \"timestamp\": \"$(date -Iseconds)\",
                \"service\": \"AI Counselor\"
            }" \
            2>/dev/null || true
    fi

    # Email notification
    if [[ -n "$ALERT_EMAIL" ]] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "AI Counselor Alert: $severity" "$ALERT_EMAIL"
    fi

    # Log to file
    echo "[$(date -Iseconds)] [$severity] $message" >> monitoring.log
}

# Check backend health
check_backend() {
    if curl -f -s --max-time 5 "${BACKEND_URL}/health" > /dev/null 2>&1; then
        log_success "Backend is healthy"
        return 0
    else
        log_error "Backend is down or unhealthy"
        send_alert "CRITICAL" "Backend service is down at $BACKEND_URL"
        return 1
    fi
}

# Check frontend health
check_frontend() {
    if curl -f -s --max-time 5 "$FRONTEND_URL" > /dev/null 2>&1; then
        log_success "Frontend is healthy"
        return 0
    else
        log_error "Frontend is down or unhealthy"
        send_alert "CRITICAL" "Frontend service is down at $FRONTEND_URL"
        return 1
    fi
}

# Check database health
check_database() {
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log_success "Database is healthy"
        return 0
    else
        log_error "Database is down or unhealthy"
        send_alert "CRITICAL" "PostgreSQL database is down"
        return 1
    fi
}

# Check Redis health
check_redis() {
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is healthy"
        return 0
    else
        log_error "Redis is down or unhealthy"
        send_alert "CRITICAL" "Redis cache is down"
        return 1
    fi
}

# Check disk space
check_disk_space() {
    local usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

    if [[ $usage -lt 80 ]]; then
        log_success "Disk usage: ${usage}%"
        return 0
    elif [[ $usage -lt 90 ]]; then
        log_warning "Disk usage is high: ${usage}%"
        send_alert "WARNING" "Disk usage is at ${usage}%"
        return 1
    else
        log_error "Disk usage is critical: ${usage}%"
        send_alert "CRITICAL" "Disk usage is at ${usage}% - immediate action required"
        return 1
    fi
}

# Check memory usage
check_memory() {
    local usage=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')

    if [[ $usage -lt 80 ]]; then
        log_success "Memory usage: ${usage}%"
        return 0
    elif [[ $usage -lt 90 ]]; then
        log_warning "Memory usage is high: ${usage}%"
        send_alert "WARNING" "Memory usage is at ${usage}%"
        return 1
    else
        log_error "Memory usage is critical: ${usage}%"
        send_alert "CRITICAL" "Memory usage is at ${usage}%"
        return 1
    fi
}

# Check CPU usage
check_cpu() {
    local usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{printf("%.0f", 100 - $1)}')

    if [[ $usage -lt 80 ]]; then
        log_success "CPU usage: ${usage}%"
        return 0
    elif [[ $usage -lt 90 ]]; then
        log_warning "CPU usage is high: ${usage}%"
        send_alert "WARNING" "CPU usage is at ${usage}%"
        return 1
    else
        log_error "CPU usage is critical: ${usage}%"
        send_alert "CRITICAL" "CPU usage is at ${usage}%"
        return 1
    fi
}

# Check container status
check_containers() {
    log_info "Container status:"

    local containers=("backend" "frontend" "db" "redis" "nginx")
    local all_healthy=true

    for container in "${containers[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$container" | grep -q "Up"; then
            log_success "  $container: running"
        else
            log_error "  $container: not running"
            send_alert "CRITICAL" "Container $container is not running"
            all_healthy=false
        fi
    done

    $all_healthy
}

# Check response time
check_response_time() {
    local start_time=$(date +%s%N)
    curl -f -s --max-time 10 "${BACKEND_URL}/health" > /dev/null 2>&1
    local end_time=$(date +%s%N)

    local response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to ms

    if [[ $response_time -lt 1000 ]]; then
        log_success "Response time: ${response_time}ms"
        return 0
    elif [[ $response_time -lt 3000 ]]; then
        log_warning "Response time is slow: ${response_time}ms"
        send_alert "WARNING" "API response time is ${response_time}ms"
        return 1
    else
        log_error "Response time is very slow: ${response_time}ms"
        send_alert "CRITICAL" "API response time is ${response_time}ms"
        return 1
    fi
}

# Check database connections
check_db_connections() {
    local connections=$(docker-compose -f "$COMPOSE_FILE" exec -T db \
        psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tr -d ' ')

    if [[ $connections -lt 150 ]]; then
        log_success "Database connections: $connections"
        return 0
    elif [[ $connections -lt 180 ]]; then
        log_warning "Database connections are high: $connections"
        send_alert "WARNING" "Database has $connections active connections"
        return 1
    else
        log_error "Database connections are critical: $connections"
        send_alert "CRITICAL" "Database has $connections active connections"
        return 1
    fi
}

# Get database size
get_db_size() {
    local size=$(docker-compose -f "$COMPOSE_FILE" exec -T db \
        psql -U postgres -t -c "SELECT pg_size_pretty(pg_database_size('aicounselor'));" 2>/dev/null | tr -d ' ')

    log_info "Database size: $size"
}

# Check cache hit rate
check_cache_hit_rate() {
    local stats=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli INFO stats 2>/dev/null | grep -E "keyspace_hits|keyspace_misses")

    if [[ -n "$stats" ]]; then
        local hits=$(echo "$stats" | grep keyspace_hits | cut -d: -f2 | tr -d '\r')
        local misses=$(echo "$stats" | grep keyspace_misses | cut -d: -f2 | tr -d '\r')
        local total=$((hits + misses))

        if [[ $total -gt 0 ]]; then
            local hit_rate=$(awk "BEGIN {printf \"%.1f\", ($hits / $total) * 100}")
            log_info "Cache hit rate: ${hit_rate}%"

            if (( $(awk "BEGIN {print ($hit_rate < 50)}") )); then
                log_warning "Cache hit rate is low"
                send_alert "WARNING" "Cache hit rate is ${hit_rate}% (target: >60%)"
            fi
        fi
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              AI Counselor - Monitoring Summary            ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
}

# Single check run
run_checks() {
    print_summary

    local checks_passed=0
    local checks_failed=0

    # Service health checks
    log_info "=== Service Health Checks ==="
    check_backend && ((checks_passed++)) || ((checks_failed++))
    check_frontend && ((checks_passed++)) || ((checks_failed++))
    check_database && ((checks_passed++)) || ((checks_failed++))
    check_redis && ((checks_passed++)) || ((checks_failed++))

    echo ""

    # Resource checks
    log_info "=== Resource Checks ==="
    check_disk_space && ((checks_passed++)) || ((checks_failed++))
    check_memory && ((checks_passed++)) || ((checks_failed++))
    check_cpu && ((checks_passed++)) || ((checks_failed++))

    echo ""

    # Container checks
    log_info "=== Container Checks ==="
    check_containers && ((checks_passed++)) || ((checks_failed++))

    echo ""

    # Performance checks
    log_info "=== Performance Checks ==="
    check_response_time && ((checks_passed++)) || ((checks_failed++))
    check_db_connections && ((checks_passed++)) || ((checks_failed++))
    get_db_size
    check_cache_hit_rate

    echo ""
    log_info "=== Summary ==="
    log_success "Checks passed: $checks_passed"
    if [[ $checks_failed -gt 0 ]]; then
        log_error "Checks failed: $checks_failed"
    else
        log_success "All checks passed!"
    fi
    echo ""
}

# Main loop
main() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║       AI Counselor - Continuous Monitoring Script        ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Starting monitoring (check interval: ${CHECK_INTERVAL}s)"
    log_info "Press Ctrl+C to stop"
    echo ""

    # Run checks continuously
    while true; do
        run_checks
        log_info "Next check in ${CHECK_INTERVAL} seconds..."
        sleep $CHECK_INTERVAL
    done
}

# Handle single run mode
if [[ "${1:-}" == "--once" ]]; then
    run_checks
    exit 0
fi

# Run main loop
main "$@"
