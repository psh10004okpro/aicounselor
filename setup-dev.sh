#!/bin/bash

# Development Setup Script for Mindful AI Counselor
# 마음이 AI 상담사 개발 환경 설정 스크립트

set -e  # Exit on error

echo "🚀 마음이 AI 상담사 개발 환경 설정을 시작합니다..."
echo "================================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if Docker is installed
echo "1️⃣  Docker 확인 중..."
if ! command -v docker &> /dev/null; then
    print_error "Docker가 설치되어 있지 않습니다."
    echo "   설치: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker 설치됨: $(docker --version)"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose가 설치되어 있지 않습니다."
    echo "   설치: https://docs.docker.com/compose/install/"
    exit 1
fi
print_success "Docker Compose 설치됨: $(docker-compose --version)"

# Check if .env exists
echo ""
echo "2️⃣  환경 변수 파일 확인 중..."
if [ ! -f .env ]; then
    print_warning ".env 파일이 없습니다. .env.example에서 복사합니다..."
    cp .env.example .env
    print_success ".env 파일 생성됨"

    echo ""
    print_warning "⚠️  중요: .env 파일을 편집하여 다음 값을 설정해야 합니다:"
    echo "   1. OPENAI_API_KEY - OpenAI API 키 (필수!)"
    echo "   2. SECRET_KEY - JWT 서명용 비밀키 (필수!)"
    echo "   3. POSTGRES_PASSWORD - 데이터베이스 비밀번호 (권장)"
    echo "   4. REDIS_PASSWORD - Redis 비밀번호 (권장)"
    echo ""
    read -p "   지금 .env 파일을 편집하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    else
        print_warning "나중에 수동으로 .env 파일을 편집하세요!"
    fi
else
    print_success ".env 파일이 존재합니다"
fi

# Check for required environment variables
echo ""
echo "3️⃣  필수 환경 변수 검증 중..."
source .env 2>/dev/null || true

MISSING_VARS=0

if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
    print_error "OPENAI_API_KEY가 설정되지 않았습니다"
    MISSING_VARS=1
else
    print_success "OPENAI_API_KEY 설정됨"
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your_secret_key_for_jwt_signing_here" ]; then
    print_warning "SECRET_KEY가 기본값입니다. 새로운 키를 생성합니다..."

    # Generate SECRET_KEY if openssl is available
    if command -v openssl &> /dev/null; then
        NEW_SECRET_KEY=$(openssl rand -hex 32)
        # Update .env file
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET_KEY/" .env
        else
            sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET_KEY/" .env
        fi
        print_success "새로운 SECRET_KEY 생성 및 저장됨"
    else
        print_error "openssl이 없어 SECRET_KEY를 생성할 수 없습니다"
        print_info "수동으로 SECRET_KEY를 설정하세요"
        MISSING_VARS=1
    fi
else
    print_success "SECRET_KEY 설정됨"
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    print_error "필수 환경 변수가 누락되었습니다. .env 파일을 확인하세요."
    exit 1
fi

# Stop any running containers
echo ""
echo "4️⃣  기존 컨테이너 정리 중..."
if docker-compose ps -q 2>/dev/null | grep -q .; then
    print_info "실행 중인 컨테이너를 중지합니다..."
    docker-compose down
    print_success "컨테이너 중지됨"
else
    print_info "실행 중인 컨테이너가 없습니다"
fi

# Pull latest images
echo ""
echo "5️⃣  Docker 이미지 가져오기 중..."
docker-compose pull
print_success "이미지 다운로드 완료"

# Build services
echo ""
echo "6️⃣  서비스 빌드 중..."
docker-compose build --no-cache
print_success "서비스 빌드 완료"

# Start services
echo ""
echo "7️⃣  서비스 시작 중..."
docker-compose up -d
print_success "서비스 시작됨"

# Wait for services to be healthy
echo ""
echo "8️⃣  서비스 상태 확인 중..."
echo "   (최대 60초 대기)"

TIMEOUT=60
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    POSTGRES_HEALTH=$(docker inspect mindful-postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")
    REDIS_HEALTH=$(docker inspect mindful-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "starting")

    if [ "$POSTGRES_HEALTH" = "healthy" ] && [ "$REDIS_HEALTH" = "healthy" ]; then
        print_success "모든 서비스가 정상 작동 중입니다!"
        break
    fi

    echo -ne "   PostgreSQL: $POSTGRES_HEALTH | Redis: $REDIS_HEALTH\r"
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    print_warning "서비스 헬스체크 타임아웃 (계속 진행합니다)"
fi

# Show service status
echo ""
echo "9️⃣  서비스 상태:"
docker-compose ps

echo ""
echo "================================================"
print_success "개발 환경 설정 완료! 🎉"
echo ""
echo "📍 접속 주소:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📝 유용한 명령어:"
echo "   로그 보기:        docker-compose logs -f"
echo "   서비스 중지:      docker-compose stop"
echo "   서비스 재시작:    docker-compose restart"
echo "   완전 삭제:        docker-compose down -v"
echo ""
echo "🧪 위기 감지 테스트:"
echo "   1. http://localhost:3000 접속"
echo "   2. \"죽고 싶어요\" 입력 (CRITICAL)"
echo "   3. \"희망이 없어요\" 입력 (HIGH)"
echo ""
print_info "자세한 내용은 QUICKSTART.md를 참조하세요"
echo "================================================"
