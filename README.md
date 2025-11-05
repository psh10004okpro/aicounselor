# 🧠 AI Counselor - Mindful AI Counseling Chatbot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

한국어 기반 AI 심리상담 챗봇 시스템. 인지행동치료(CBT) 기반 대화와 3단계 위기 감지 시스템을 갖춘 프로덕션급 애플리케이션.

## 📋 목차

- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [설치 가이드](#설치-가이드)
- [환경 변수](#환경-변수)
- [API 문서](#api-문서)
- [테스트](#테스트)
- [배포](#배포)
- [라이선스](#라이선스)

## ✨ 주요 기능

### 🤖 AI 대화 시스템
- GPT-4o-mini 기반 실시간 상담
- 인지행동치료(CBT) 접근
- SSE 스트리밍 응답
- 한국어 최적화

### 🚨 3단계 위기 감지
1. 키워드 감지 (100+ 한국어 키워드)
2. GPT-4 분석
3. 구조화된 검증

### 🔐 엔터프라이즈 보안
- JWT 인증 (15분/7일)
- AES-256 암호화
- 7-Layer Security Middleware
- HIPAA/GDPR 준수

### ⚡ 고성능 캐싱
- 60% Cache Hit Rate
- FAQ + Semantic + API 3-tier
- Redis 기반

## 🛠 기술 스택

**Backend**: Python 3.11, FastAPI, PostgreSQL, Redis, OpenAI
**Frontend**: Next.js 14, TypeScript, React 18, Tailwind CSS
**DevOps**: Docker, Docker Compose, GitHub Actions

## 🚀 빠른 시작

```bash
# 1. 클론
git clone https://github.com/yourusername/aicounselor.git
cd aicounselor

# 2. 환경 변수 설정
cp .env.example .env
# .env에서 OPENAI_API_KEY 설정

# 3. 실행
chmod +x setup-dev.sh
./setup-dev.sh

# 4. 접속
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
```

## 📦 설치 가이드

### Docker Compose (권장)

```bash
# 빌드 및 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### Makefile 명령어

```bash
make start          # 시작
make stop           # 중지
make logs           # 로그
make health         # 헬스 체크
make test           # 테스트
make clean          # 정리
```

## ⚙️ 환경 변수

필수 환경 변수:

```env
OPENAI_API_KEY=sk-...
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/aicounselor
REDIS_URL=redis://redis:6379/0
```

전체 환경 변수는 `.env.example` 참조

## 📚 API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

주요 엔드포인트:
```
POST /auth/login           # 로그인
POST /auth/register        # 회원가입
POST /chat/message         # 채팅 (non-streaming)
POST /chat/stream          # 채팅 (streaming)
```

## 🧪 테스트

```bash
# Backend
cd backend
pytest --cov=app

# Frontend
cd frontend
npm test

# 전체
make test
```

60+ 테스트 케이스 포함

## 🚀 배포

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 환경별 설정
- Development: `docker-compose.yml`
- Production: `docker-compose.prod.yml`

## 📊 성능

- API Response: < 2초
- Crisis Detection: < 3초
- Cache Hit Rate: > 60%
- Token Generation: < 1초

## 🔒 보안

- JWT with Blacklisting
- AES-256 Encryption
- Rate Limiting: 100/min, 1000/hour
- SQL/XSS Protection
- CSRF Protection

## 📄 라이선스

MIT License. [LICENSE](./LICENSE) 참조

## 📞 지원

- Issues: [GitHub Issues](https://github.com/yourusername/aicounselor/issues)
- Email: support@aicounselor.com

## ⚠️ 면책 조항

이 시스템은 전문 정신건강 서비스를 대체하지 않습니다.

**긴급 상황**: 1393(자살예방), 119(응급)

---

Made with ❤️ by AI Counselor Team
