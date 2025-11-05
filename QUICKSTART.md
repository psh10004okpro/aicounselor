# 🚀 Quick Start Guide / 빠른 시작 가이드

마음이 AI 상담사를 5분 안에 시작하세요!

## 📋 Prerequisites / 사전 요구사항

- Docker & Docker Compose 설치됨
- OpenAI API Key ([발급받기](https://platform.openai.com/api-keys))
- 최소 2GB RAM

## ⚡ 5분 설치 (Quick Setup)

### 1️⃣ 프로젝트 클론

```bash
git clone <repository-url>
cd mindful-ai-counselor
```

### 2️⃣ 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 vim, code 등 선호하는 에디터 사용
```

**필수 설정 항목**:
```env
# OpenAI API Key (필수!)
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# 보안 키 생성 (필수!)
SECRET_KEY=$(openssl rand -hex 32)

# 데이터베이스 비밀번호 변경 (권장)
POSTGRES_PASSWORD=your_secure_password_123

# Redis 비밀번호 변경 (권장)
REDIS_PASSWORD=your_redis_password_456
```

💡 **Tip**: `openssl rand -hex 32` 명령어로 안전한 SECRET_KEY를 생성할 수 있습니다.

### 3️⃣ Docker Compose 실행

```bash
# 백그라운드에서 모든 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 4️⃣ 접속 확인

브라우저에서 다음 주소를 열어보세요:

- **Frontend (사용자 UI)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🎯 첫 대화 테스트

1. http://localhost:3000 접속
2. "안녕하세요"라고 입력
3. 마음이가 응답하는지 확인!

### 위기 감지 테스트

다음 메시지들로 위기 감지 시스템을 테스트해보세요:

**⚠️ CRITICAL 등급 (빨간색 경고)**:
- "죽고 싶어요"
- "자살하고 싶어요"

**🟠 HIGH 등급 (노란색 경고)**:
- "희망이 없어요"
- "살아있는 의미가 없어요"

**🟡 MEDIUM 등급**:
- "너무 힘들어요"
- "우울해요"

각 등급에 따라 다른 UI와 한국 위기 상담 번호가 표시됩니다.

## 📊 서비스 상태 확인

```bash
# 모든 서비스 상태 확인
docker-compose ps

# 특정 서비스 로그 보기
docker-compose logs backend
docker-compose logs frontend
docker-compose logs postgres
docker-compose logs redis

# 실시간 로그 스트리밍
docker-compose logs -f backend
```

## 🔍 데이터베이스 확인

```bash
# PostgreSQL 접속
docker exec -it mindful-postgres psql -U postgres -d mindful_counselor

# 테이블 목록 확인
\dt

# 사용자 확인
SELECT user_id, email_hash, is_anonymous, created_at FROM users;

# 대화 확인
SELECT conversation_id, title, created_at FROM conversations;

# 위기 로그 확인
SELECT * FROM crisis_logs ORDER BY detected_at DESC LIMIT 5;

# 나가기
\q
```

## 🛑 서비스 중지 및 재시작

```bash
# 서비스 중지 (데이터 유지)
docker-compose stop

# 서비스 재시작
docker-compose start

# 완전 종료 (컨테이너 삭제, 데이터는 유지)
docker-compose down

# 데이터까지 모두 삭제
docker-compose down -v
```

## 🔧 문제 해결 (Troubleshooting)

### 1. "Cannot connect to OpenAI API" 오류

**원인**: OpenAI API Key가 설정되지 않았거나 잘못됨

**해결**:
```bash
# .env 파일에서 OPENAI_API_KEY 확인
cat .env | grep OPENAI_API_KEY

# 유효한 키인지 테스트
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 2. "Database connection failed" 오류

**원인**: PostgreSQL이 준비되지 않았거나 비밀번호 불일치

**해결**:
```bash
# PostgreSQL 상태 확인
docker-compose ps postgres

# PostgreSQL 로그 확인
docker-compose logs postgres

# 헬스체크 확인
docker inspect mindful-postgres | grep -A 10 Health
```

### 3. Frontend가 Backend에 연결되지 않음

**원인**: CORS 설정 또는 URL 불일치

**해결**:
```bash
# .env에서 설정 확인
cat .env | grep -E "(NEXT_PUBLIC_API_URL|ALLOWED_ORIGINS)"

# Backend 로그에서 CORS 오류 확인
docker-compose logs backend | grep -i cors

# Frontend에서 Backend URL 확인
docker exec -it mindful-frontend env | grep NEXT_PUBLIC
```

### 4. Redis connection error

**원인**: Redis 비밀번호 불일치

**해결**:
```bash
# Redis 접속 테스트
docker exec -it mindful-redis redis-cli -a your_redis_password_456 ping
# PONG이 출력되어야 함

# .env의 REDIS_PASSWORD와 docker-compose.yml 확인
```

### 5. 세션 초기화 중... 메시지가 계속 표시

**원인**: Backend의 /auth/anonymous 엔드포인트 오류

**해결**:
```bash
# Backend 로그 확인
docker-compose logs backend | tail -50

# API 직접 테스트
curl -X POST http://localhost:8000/auth/anonymous \
  -H "Content-Type: application/json"

# 응답이 {"session_token": "...", "user": {...}} 형태여야 함
```

## 📱 API 테스트

### Anonymous 세션 생성
```bash
curl -X POST http://localhost:8000/auth/anonymous \
  -H "Content-Type: application/json"
```

### 채팅 메시지 전송 (Non-streaming)
```bash
SESSION_TOKEN="your_session_token_from_above"

curl -X POST "http://localhost:8000/chat/message?session_token=$SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "conversation_id": null,
    "stream": false
  }'
```

### 건강 체크
```bash
curl http://localhost:8000/health
```

## 🔄 데이터베이스 마이그레이션

데이터베이스 스키마 변경 시:

```bash
# 백엔드 컨테이너 접속
docker exec -it mindful-backend bash

# 마이그레이션 실행
cd /app
alembic upgrade head

# 나가기
exit
```

## 📈 성능 모니터링

### Redis 캐시 상태
```bash
# Redis 접속
docker exec -it mindful-redis redis-cli -a your_redis_password_456

# 캐시 키 확인
KEYS cache:*

# 캐시 히트/미스 통계
INFO stats

# 나가기
exit
```

### 데이터베이스 성능
```bash
# PostgreSQL 접속
docker exec -it mindful-postgres psql -U postgres -d mindful_counselor

# 테이블 크기 확인
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# 나가기
\q
```

## 🎓 다음 단계

1. **커스터마이징**:
   - `backend/app/services/openai_service.py`에서 "마음이" 시스템 프롬프트 수정
   - `frontend/components/`에서 UI 컴포넌트 커스터마이징

2. **위기 감지 설정**:
   - `backend/app/services/crisis_detector.py`에서 키워드 추가/수정
   - `CRISIS_DETECTION.md` 참조

3. **프로덕션 배포**:
   - README.md의 "Production Deployment" 섹션 참조
   - HTTPS 설정
   - 도메인 연결
   - 환경 변수 보안 강화

4. **모니터링 설정**:
   - Sentry 연동
   - 로그 수집 (ELK Stack, CloudWatch 등)
   - 알림 설정

## 💡 유용한 명령어 모음

```bash
# 전체 재빌드
docker-compose up -d --build

# 특정 서비스만 재시작
docker-compose restart backend

# 컨테이너 내부 접속
docker exec -it mindful-backend bash
docker exec -it mindful-frontend sh

# 로그 저장
docker-compose logs > logs.txt

# 리소스 사용량 확인
docker stats
```

## 📞 도움이 필요하신가요?

- **Issues**: GitHub Issues에 문제 보고
- **Documentation**: README.md 전체 문서 참조
- **Crisis Detection**: CRISIS_DETECTION.md 참조

## ⚠️ 중요 공지

이 시스템은 AI 상담 도우미로, 전문 정신건강 치료를 대체할 수 없습니다.

**위기 상황 시 즉시 연락하세요**:
- 자살예방상담전화: **1393** (24시간 무료)
- 청소년전화: **1388**
- 정신건강위기상담전화: **1577-0199**
- 응급: **119**

---

**Happy Coding! 🚀**

문제가 발생하면 위의 문제 해결 섹션을 먼저 확인하세요.
