.PHONY: help setup start stop restart logs clean test backend-shell db-shell redis-shell health

# Default target
help:
	@echo "마음이 AI 상담사 - 개발 명령어"
	@echo "================================"
	@echo ""
	@echo "설정 및 시작:"
	@echo "  make setup        - 초기 개발 환경 설정 및 시작"
	@echo "  make start        - 모든 서비스 시작"
	@echo "  make stop         - 모든 서비스 중지"
	@echo "  make restart      - 모든 서비스 재시작"
	@echo ""
	@echo "모니터링:"
	@echo "  make logs         - 모든 서비스 로그 보기 (실시간)"
	@echo "  make logs-backend - 백엔드 로그만 보기"
	@echo "  make logs-frontend - 프론트엔드 로그만 보기"
	@echo "  make health       - 서비스 상태 확인"
	@echo ""
	@echo "개발 도구:"
	@echo "  make backend-shell - 백엔드 컨테이너 접속"
	@echo "  make db-shell     - PostgreSQL 접속"
	@echo "  make redis-shell  - Redis CLI 접속"
	@echo ""
	@echo "테스트 및 정리:"
	@echo "  make test         - 백엔드 테스트 실행"
	@echo "  make clean        - 모든 컨테이너 및 볼륨 삭제"
	@echo "  make rebuild      - 컨테이너 재빌드"
	@echo ""

# Setup development environment
setup:
	@echo "🚀 개발 환경 설정 중..."
	@bash setup-dev.sh

# Start all services
start:
	@echo "▶️  서비스 시작 중..."
	@docker-compose up -d
	@echo "✅ 서비스 시작됨"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

# Stop all services
stop:
	@echo "⏹️  서비스 중지 중..."
	@docker-compose stop
	@echo "✅ 서비스 중지됨"

# Restart all services
restart:
	@echo "🔄 서비스 재시작 중..."
	@docker-compose restart
	@echo "✅ 서비스 재시작됨"

# View logs (all services)
logs:
	@docker-compose logs -f

# View backend logs only
logs-backend:
	@docker-compose logs -f backend

# View frontend logs only
logs-frontend:
	@docker-compose logs -f frontend

# View postgres logs
logs-db:
	@docker-compose logs -f postgres

# View redis logs
logs-redis:
	@docker-compose logs -f redis

# Check service health
health:
	@echo "🏥 서비스 상태 확인 중..."
	@docker-compose ps
	@echo ""
	@echo "백엔드 헬스체크:"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ 백엔드 응답 없음"

# Access backend container shell
backend-shell:
	@echo "🐚 백엔드 컨테이너 접속 중..."
	@docker exec -it mindful-backend bash

# Access frontend container shell
frontend-shell:
	@echo "🐚 프론트엔드 컨테이너 접속 중..."
	@docker exec -it mindful-frontend sh

# Access PostgreSQL
db-shell:
	@echo "🗄️  PostgreSQL 접속 중..."
	@docker exec -it mindful-postgres psql -U postgres -d mindful_counselor

# Access Redis CLI
redis-shell:
	@echo "🔴 Redis CLI 접속 중..."
	@docker exec -it mindful-redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2)

# Run backend tests
test:
	@echo "🧪 백엔드 테스트 실행 중..."
	@docker exec -it mindful-backend pytest tests/ -v

# Run backend tests with coverage
test-coverage:
	@echo "🧪 테스트 커버리지 확인 중..."
	@docker exec -it mindful-backend pytest tests/ --cov=app --cov-report=html --cov-report=term

# Clean up everything
clean:
	@echo "🧹 모든 컨테이너 및 볼륨 삭제 중..."
	@read -p "⚠️  모든 데이터가 삭제됩니다. 계속하시겠습니까? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "✅ 정리 완료"; \
	else \
		echo "❌ 취소됨"; \
	fi

# Rebuild containers
rebuild:
	@echo "🔨 컨테이너 재빌드 중..."
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "✅ 재빌드 완료"

# Database migrations
db-migrate:
	@echo "🗄️  데이터베이스 마이그레이션 실행 중..."
	@docker exec -it mindful-backend alembic upgrade head
	@echo "✅ 마이그레이션 완료"

# Create new migration
db-migration-create:
	@read -p "마이그레이션 이름을 입력하세요: " name; \
	docker exec -it mindful-backend alembic revision --autogenerate -m "$$name"

# Database backup
db-backup:
	@echo "💾 데이터베이스 백업 중..."
	@mkdir -p backups
	@docker exec mindful-postgres pg_dump -U postgres mindful_counselor > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ 백업 완료: backups/backup_$$(date +%Y%m%d_%H%M%S).sql"

# Database restore
db-restore:
	@echo "📥 데이터베이스 복원 중..."
	@ls -1 backups/*.sql 2>/dev/null || (echo "❌ 백업 파일이 없습니다" && exit 1)
	@read -p "복원할 백업 파일명을 입력하세요: " file; \
	cat backups/$$file | docker exec -i mindful-postgres psql -U postgres mindful_counselor
	@echo "✅ 복원 완료"

# View database tables
db-tables:
	@echo "📊 데이터베이스 테이블 목록:"
	@docker exec -it mindful-postgres psql -U postgres -d mindful_counselor -c '\dt'

# View recent crisis logs
db-crisis-logs:
	@echo "🚨 최근 위기 로그 (최근 10개):"
	@docker exec -it mindful-postgres psql -U postgres -d mindful_counselor -c \
		"SELECT log_id, risk_level, detected_keywords, detected_at FROM crisis_logs ORDER BY detected_at DESC LIMIT 10;"

# Redis cache stats
redis-stats:
	@echo "📊 Redis 캐시 통계:"
	@docker exec -it mindful-redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2) INFO stats

# Redis flush cache
redis-flush:
	@echo "🗑️  Redis 캐시 초기화 중..."
	@read -p "⚠️  모든 캐시가 삭제됩니다. 계속하시겠습니까? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker exec -it mindful-redis redis-cli -a $$(grep REDIS_PASSWORD .env | cut -d '=' -f2) FLUSHALL; \
		echo "✅ 캐시 초기화 완료"; \
	else \
		echo "❌ 취소됨"; \
	fi

# Development mode (with hot reload)
dev:
	@echo "🔥 개발 모드로 시작 중 (hot reload)..."
	@docker-compose up

# Production build
prod-build:
	@echo "🏭 프로덕션 빌드 중..."
	@docker-compose -f docker-compose.prod.yml build

# Show resource usage
stats:
	@echo "📈 리소스 사용량:"
	@docker stats --no-stream mindful-backend mindful-frontend mindful-postgres mindful-redis

# Update dependencies
update-deps:
	@echo "📦 백엔드 의존성 업데이트 중..."
	@docker exec -it mindful-backend pip install --upgrade -r requirements.txt
	@echo "📦 프론트엔드 의존성 업데이트 중..."
	@docker exec -it mindful-frontend npm update
	@echo "✅ 의존성 업데이트 완료"
