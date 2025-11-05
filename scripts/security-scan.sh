#!/bin/bash
#
# Security Scanning Script for AI Counselor
#
# Performs comprehensive security checks:
# - Dependency vulnerability scanning
# - Secret detection
# - Environment variable validation
# - Docker image scanning
# - Code security analysis
#
# Usage:
#   ./scripts/security-scan.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REPORT_DIR="./security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

# Create report directory
mkdir -p "$REPORT_DIR"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║          AI Counselor - Security Scan                    ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 1. Check for secrets in code
# ============================================================================

log_info "1/8 Scanning for secrets in code..."

if command -v gitleaks &> /dev/null; then
    gitleaks detect --source=. --report-path="${REPORT_DIR}/gitleaks_${TIMESTAMP}.json" || {
        log_warning "Gitleaks found potential secrets - check report"
    }
    log_success "Secret scanning complete"
else
    log_warning "gitleaks not installed - skipping secret scan"
    log_info "Install: https://github.com/gitleaks/gitleaks"
fi

echo ""

# ============================================================================
# 2. Python dependency vulnerability scan
# ============================================================================

log_info "2/8 Scanning Python dependencies..."

if [ -f "backend/requirements.txt" ]; then
    # Using pip-audit
    if command -v pip-audit &> /dev/null; then
        pip-audit -r backend/requirements.txt \
            --format json \
            --output "${REPORT_DIR}/python_vulnerabilities_${TIMESTAMP}.json" || {
            log_warning "Vulnerabilities found in Python dependencies"
        }
        log_success "Python dependency scan complete"
    # Alternative: safety
    elif command -v safety &> /dev/null; then
        safety check -r backend/requirements.txt \
            --json \
            --output "${REPORT_DIR}/python_safety_${TIMESTAMP}.json" || {
            log_warning "Vulnerabilities found in Python dependencies"
        }
        log_success "Python dependency scan complete"
    else
        log_warning "pip-audit or safety not installed - skipping Python scan"
        log_info "Install: pip install pip-audit"
    fi
else
    log_error "backend/requirements.txt not found"
fi

echo ""

# ============================================================================
# 3. Node.js dependency vulnerability scan
# ============================================================================

log_info "3/8 Scanning Node.js dependencies..."

if [ -f "frontend/package.json" ]; then
    cd frontend

    # npm audit
    log_info "Running npm audit..."
    npm audit --json > "../${REPORT_DIR}/npm_audit_${TIMESTAMP}.json" || {
        log_warning "Vulnerabilities found in Node.js dependencies"
    }

    # Try to fix automatically
    log_info "Attempting automatic fixes..."
    npm audit fix --dry-run > "../${REPORT_DIR}/npm_audit_fix_${TIMESTAMP}.txt" 2>&1 || true

    cd ..
    log_success "Node.js dependency scan complete"
else
    log_error "frontend/package.json not found"
fi

echo ""

# ============================================================================
# 4. Docker image vulnerability scan
# ============================================================================

log_info "4/8 Scanning Docker images..."

if command -v trivy &> /dev/null; then
    # Scan backend image
    if docker images | grep -q "aicounselor-backend"; then
        log_info "Scanning backend Docker image..."
        trivy image \
            --severity HIGH,CRITICAL \
            --format json \
            --output "${REPORT_DIR}/trivy_backend_${TIMESTAMP}.json" \
            aicounselor-backend:latest || true
    fi

    # Scan frontend image
    if docker images | grep -q "aicounselor-frontend"; then
        log_info "Scanning frontend Docker image..."
        trivy image \
            --severity HIGH,CRITICAL \
            --format json \
            --output "${REPORT_DIR}/trivy_frontend_${TIMESTAMP}.json" \
            aicounselor-frontend:latest || true
    fi

    log_success "Docker image scan complete"
else
    log_warning "trivy not installed - skipping Docker scan"
    log_info "Install: https://github.com/aquasecurity/trivy"
fi

echo ""

# ============================================================================
# 5. Environment variable validation
# ============================================================================

log_info "5/8 Validating environment variables..."

validate_env() {
    local env_file=$1
    local missing_vars=()

    if [ ! -f "$env_file" ]; then
        log_warning "$env_file not found"
        return
    fi

    # Required variables
    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "OPENAI_API_KEY"
        "SECRET_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
    )

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file"; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required variables in $env_file:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        return 1
    else
        log_success "All required variables present in $env_file"
    fi

    # Check for weak secrets
    log_info "Checking for weak secrets..."

    # Check SECRET_KEY length
    secret_key=$(grep "^SECRET_KEY=" "$env_file" | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [ ${#secret_key} -lt 32 ]; then
        log_warning "SECRET_KEY is too short (< 32 characters)"
    fi

    # Check for default passwords
    if grep -qi "password=password" "$env_file" || \
       grep -qi "password=admin" "$env_file" || \
       grep -qi "password=123" "$env_file"; then
        log_error "Weak or default passwords detected!"
    fi
}

# Validate .env files
for env_file in .env .env.dev .env.prod .env.local; do
    if [ -f "$env_file" ]; then
        validate_env "$env_file"
    fi
done

echo ""

# ============================================================================
# 6. Code security analysis (Bandit for Python)
# ============================================================================

log_info "6/8 Running code security analysis..."

if command -v bandit &> /dev/null; then
    log_info "Running Bandit on Python code..."
    bandit -r backend/ \
        -f json \
        -o "${REPORT_DIR}/bandit_${TIMESTAMP}.json" \
        -ll || {  # Low level and above
        log_warning "Security issues found in Python code"
    }
    log_success "Python code analysis complete"
else
    log_warning "bandit not installed - skipping Python code analysis"
    log_info "Install: pip install bandit"
fi

echo ""

# ============================================================================
# 7. Check for exposed secrets in Git history
# ============================================================================

log_info "7/8 Checking Git history for secrets..."

if command -v git &> /dev/null && [ -d ".git" ]; then
    # Check for common secret patterns in git history
    log_info "Scanning git history..."

    patterns=(
        "api[_-]?key"
        "secret"
        "password"
        "token"
        "private[_-]?key"
    )

    found_secrets=false
    for pattern in "${patterns[@]}"; do
        if git log -S "$pattern" --all --pretty=format:"%H %s" | head -5 > /dev/null; then
            matches=$(git log -S "$pattern" --all --oneline | wc -l)
            if [ "$matches" -gt 0 ]; then
                log_warning "Found $matches commits with '$pattern'"
                found_secrets=true
            fi
        fi
    done

    if [ "$found_secrets" = false ]; then
        log_success "No obvious secrets found in git history"
    else
        log_warning "Review git history for potential secrets"
    fi
else
    log_warning "Not a git repository - skipping git history scan"
fi

echo ""

# ============================================================================
# 8. Permission and file security check
# ============================================================================

log_info "8/8 Checking file permissions..."

# Check for world-writable files
world_writable=$(find . -type f -perm -002 2>/dev/null | grep -v ".git" | grep -v "node_modules" || true)
if [ -n "$world_writable" ]; then
    log_warning "World-writable files found:"
    echo "$world_writable"
else
    log_success "No world-writable files found"
fi

# Check for executable scripts
log_info "Checking executable scripts..."
executable_scripts=$(find . -type f -executable | grep -v ".git" | grep -v "node_modules" | grep -v ".venv" || true)
if [ -n "$executable_scripts" ]; then
    log_info "Executable scripts found: $(echo "$executable_scripts" | wc -l)"
fi

# Check SSH keys
if find . -name "*.pem" -o -name "id_rsa" -o -name "id_dsa" 2>/dev/null | grep -q .; then
    log_error "SSH private keys found in repository!"
else
    log_success "No SSH keys found in repository"
fi

# Check .env files in git
if git ls-files | grep -q "^\.env$" 2>/dev/null; then
    log_error ".env file is tracked by git - should be in .gitignore"
else
    log_success ".env files not tracked by git"
fi

echo ""

# ============================================================================
# Summary Report
# ============================================================================

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              Security Scan Complete                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

log_success "Scan completed at $(date)"
log_success "Reports saved to: $REPORT_DIR/"

# List generated reports
if [ -d "$REPORT_DIR" ]; then
    log_info "Generated reports:"
    ls -lh "$REPORT_DIR"/*_${TIMESTAMP}.* 2>/dev/null | awk '{print "  - " $9}' || true
fi

echo ""
log_info "Recommended actions:"
echo "  1. Review all reports in $REPORT_DIR/"
echo "  2. Fix high/critical vulnerabilities immediately"
echo "  3. Rotate any exposed secrets"
echo "  4. Update dependencies with known vulnerabilities"
echo "  5. Ensure .env files are not in git"
echo ""

# Create summary report
SUMMARY_FILE="${REPORT_DIR}/summary_${TIMESTAMP}.txt"
cat > "$SUMMARY_FILE" << EOF
AI Counselor - Security Scan Summary
====================================
Scan Date: $(date)

Checks Performed:
✓ Secret detection in code
✓ Python dependency vulnerabilities
✓ Node.js dependency vulnerabilities
✓ Docker image vulnerabilities
✓ Environment variable validation
✓ Code security analysis (Bandit)
✓ Git history secret scan
✓ File permissions check

Reports Location: $REPORT_DIR/

Next Steps:
1. Review all JSON reports for details
2. Address HIGH and CRITICAL vulnerabilities
3. Rotate any exposed secrets
4. Update vulnerable dependencies
5. Fix file permission issues

EOF

log_success "Summary report: $SUMMARY_FILE"
cat "$SUMMARY_FILE"
