#!/bin/bash
#
# System Verification Script for AI Counselor
#
# Verifies all components are properly configured and operational:
# - Docker and Docker Compose
# - Environment variables
# - Database connectivity
# - Redis connectivity
# - API endpoints
# - Frontend build
# - All tests passing
#
# Usage:
#   ./scripts/verify-system.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MAX_WAIT=60  # Maximum wait time for services (seconds)

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

test_passed() {
    log_success "$1"
    ((TESTS_PASSED++))
}

test_failed() {
    log_error "$1"
    ((TESTS_FAILED++))
}

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║       AI Counselor - System Verification                 ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 1. Check prerequisites
# ============================================================================

log_info "Step 1/12: Checking prerequisites..."

# Check Docker
if command -v docker &> /dev/null; then
    test_passed "Docker is installed ($(docker --version))"
else
    test_failed "Docker is not installed"
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    test_passed "Docker Compose is installed ($(docker-compose --version))"
else
    test_failed "Docker Compose is not installed"
fi

# Check Python
if command -v python3 &> /dev/null; then
    test_passed "Python3 is installed ($(python3 --version))"
else
    test_failed "Python3 is not installed"
fi

# Check Node.js
if command -v node &> /dev/null; then
    test_passed "Node.js is installed ($(node --version))"
else
    test_failed "Node.js is not installed"
fi

echo ""

# ============================================================================
# 2. Verify project structure
# ============================================================================

log_info "Step 2/12: Verifying project structure..."

required_dirs=(
    "backend"
    "frontend"
    "database"
    "nginx"
    "scripts"
    "tests"
    "docs"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        test_passed "Directory exists: $dir"
    else
        test_failed "Directory missing: $dir"
    fi
done

echo ""

# ============================================================================
# 3. Check required files
# ============================================================================

log_info "Step 3/12: Checking required files..."

required_files=(
    "docker-compose.yml"
    "docker-compose.prod.yml"
    "README.md"
    "OPERATIONS.md"
    "backend/requirements.txt"
    "backend/Dockerfile"
    "frontend/package.json"
    "frontend/Dockerfile"
    "database/schema.sql"
    "deploy.sh"
    "rollback.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        test_passed "File exists: $file"
    else
        test_failed "File missing: $file"
    fi
done

echo ""

# ============================================================================
# 4. Validate environment variables
# ============================================================================

log_info "Step 4/12: Validating environment variables..."

# Check if .env file exists
if [ -f ".env" ]; then
    test_passed ".env file exists"

    # Source environment variables
    set -a
    source .env
    set +a

    # Check required variables
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "OPENAI_API_KEY"
        "SECRET_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [ -n "${!var}" ]; then
            test_passed "Environment variable set: $var"
        else
            test_failed "Environment variable missing: $var"
        fi
    done
else
    test_failed ".env file not found"
    log_warning "Create .env file from .env.example"
fi

echo ""

# ============================================================================
# 5. Check Docker services
# ============================================================================

log_info "Step 5/12: Checking Docker services..."

if docker-compose ps | grep -q "Up"; then
    log_info "Docker Compose services are running:"
    docker-compose ps
    echo ""

    # Check individual services
    services=("backend" "frontend" "db" "redis" "nginx")

    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            test_passed "Service running: $service"
        else
            test_failed "Service not running: $service"
        fi
    done
else
    log_warning "Docker Compose services not running"
    log_info "Start services with: docker-compose up -d"
fi

echo ""

# ============================================================================
# 6. Test database connectivity
# ============================================================================

log_info "Step 6/12: Testing database connectivity..."

if docker-compose ps db | grep -q "Up"; then
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        test_passed "PostgreSQL is ready"

        # Check if database exists
        if docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw aicounselor; then
            test_passed "Database 'aicounselor' exists"

            # Check extensions
            pgvector_check=$(docker-compose exec -T db psql -U postgres -d aicounselor -c "SELECT * FROM pg_extension WHERE extname='vector';" | wc -l)
            if [ "$pgvector_check" -gt 2 ]; then
                test_passed "pgvector extension installed"
            else
                test_failed "pgvector extension not installed"
            fi
        else
            test_failed "Database 'aicounselor' does not exist"
        fi
    else
        test_failed "PostgreSQL is not ready"
    fi
else
    test_warning "PostgreSQL container not running"
fi

echo ""

# ============================================================================
# 7. Test Redis connectivity
# ============================================================================

log_info "Step 7/12: Testing Redis connectivity..."

if docker-compose ps redis | grep -q "Up"; then
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        test_passed "Redis is responding"

        # Check Redis info
        redis_version=$(docker-compose exec -T redis redis-cli INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')
        log_info "Redis version: $redis_version"
    else
        test_failed "Redis is not responding"
    fi
else
    log_warning "Redis container not running"
fi

echo ""

# ============================================================================
# 8. Test backend API
# ============================================================================

log_info "Step 8/12: Testing backend API..."

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

# Wait for backend to be ready
log_info "Waiting for backend at $BACKEND_URL..."
wait_count=0
while ! curl -f -s "$BACKEND_URL/health" > /dev/null 2>&1; do
    if [ $wait_count -gt $MAX_WAIT ]; then
        test_failed "Backend did not start within ${MAX_WAIT}s"
        break
    fi
    sleep 2
    ((wait_count+=2))
done

if curl -f -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    test_passed "Backend API is responding"

    # Test health endpoint
    health_response=$(curl -s "$BACKEND_URL/health")
    if echo "$health_response" | grep -q "healthy"; then
        test_passed "Backend health check passed"
        log_info "Health response: $health_response"
    else
        test_failed "Backend health check failed"
    fi

    # Test API docs
    if curl -f -s "$BACKEND_URL/docs" > /dev/null 2>&1; then
        test_passed "API documentation accessible at $BACKEND_URL/docs"
    else
        test_warning "API documentation not accessible"
    fi
else
    test_failed "Backend API not responding"
fi

echo ""

# ============================================================================
# 9. Test frontend
# ============================================================================

log_info "Step 9/12: Testing frontend..."

FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Wait for frontend to be ready
log_info "Waiting for frontend at $FRONTEND_URL..."
wait_count=0
while ! curl -f -s "$FRONTEND_URL" > /dev/null 2>&1; do
    if [ $wait_count -gt $MAX_WAIT ]; then
        test_failed "Frontend did not start within ${MAX_WAIT}s"
        break
    fi
    sleep 2
    ((wait_count+=2))
done

if curl -f -s "$FRONTEND_URL" > /dev/null 2>&1; then
    test_passed "Frontend is responding"
else
    test_failed "Frontend not responding"
fi

echo ""

# ============================================================================
# 10. Run backend tests
# ============================================================================

log_info "Step 10/12: Running backend tests..."

if [ -d "backend/tests" ]; then
    log_info "Running pytest..."

    cd backend
    if command -v pytest &> /dev/null; then
        if pytest tests/ -v --tb=short > /tmp/pytest_output.txt 2>&1; then
            test_passed "All backend tests passed"
        else
            test_failed "Some backend tests failed"
            log_info "Check /tmp/pytest_output.txt for details"
        fi
    else
        log_warning "pytest not installed - skipping backend tests"
    fi
    cd ..
else
    log_warning "Backend tests directory not found"
fi

echo ""

# ============================================================================
# 11. Check cache functionality
# ============================================================================

log_info "Step 11/12: Testing cache functionality..."

if docker-compose ps redis | grep -q "Up"; then
    # Check cache keys
    key_count=$(docker-compose exec -T redis redis-cli DBSIZE | tr -d '\r')
    log_info "Redis keys in cache: $key_count"

    if [ "$key_count" -gt 0 ]; then
        test_passed "Cache is populated"
    else
        log_warning "Cache is empty - may need warming"
        log_info "Run: python scripts/cache-warming.py"
    fi

    # Check cache memory
    memory_used=$(docker-compose exec -T redis redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    log_info "Cache memory usage: $memory_used"
else
    test_failed "Redis not running - cannot test cache"
fi

echo ""

# ============================================================================
# 12. Performance checks
# ============================================================================

log_info "Step 12/12: Performance checks..."

# Check backend response time
if curl -f -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    response_time=$(curl -o /dev/null -s -w '%{time_total}' "$BACKEND_URL/health")
    response_time_ms=$(echo "$response_time * 1000" | bc)

    if (( $(echo "$response_time < 1.0" | bc -l) )); then
        test_passed "Backend response time: ${response_time_ms}ms (< 1000ms)"
    else
        test_warning "Backend response time: ${response_time_ms}ms (> 1000ms)"
    fi
fi

# Check database connections
if docker-compose ps db | grep -q "Up"; then
    connections=$(docker-compose exec -T db psql -U postgres -t -c "SELECT count(*) FROM pg_stat_activity;" | tr -d ' \r')
    log_info "Active database connections: $connections"

    if [ "$connections" -lt 50 ]; then
        test_passed "Database connections within limits"
    else
        test_warning "High number of database connections"
    fi
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              Verification Complete                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

total_tests=$((TESTS_PASSED + TESTS_FAILED))
success_rate=0
if [ "$total_tests" -gt 0 ]; then
    success_rate=$(echo "scale=1; $TESTS_PASSED * 100 / $total_tests" | bc)
fi

log_info "Test Results:"
echo "  ✓ Passed: $TESTS_PASSED"
echo "  ✗ Failed: $TESTS_FAILED"
echo "  Total:  $total_tests"
echo "  Success Rate: ${success_rate}%"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    log_success "All verification checks passed! System is ready ✅"
    echo ""
    log_info "Next steps:"
    echo "  1. Access frontend: $FRONTEND_URL"
    echo "  2. Access API docs: $BACKEND_URL/docs"
    echo "  3. Run E2E tests: python tests/e2e/test_integration.py"
    echo "  4. Run load tests: locust -f tests/load_test.py"
    echo ""
    exit 0
else
    log_error "Some verification checks failed ⚠️"
    echo ""
    log_info "Troubleshooting:"
    echo "  1. Check Docker services: docker-compose ps"
    echo "  2. View logs: docker-compose logs"
    echo "  3. Restart services: docker-compose restart"
    echo "  4. See OPERATIONS.md for detailed troubleshooting"
    echo ""
    exit 1
fi
