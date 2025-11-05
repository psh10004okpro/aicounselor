# CBT 동적 프롬프트 시스템 (CBT Dynamic Prompt System)

## 개요 (Overview)

AI 상담사에 인지행동치료(CBT) 6단계 프레임워크를 통합하여 사용자의 치료 진행 상황에 따라 동적으로 적응하는 지능형 상담 시스템입니다.

The AI Counselor implements a sophisticated 6-stage Cognitive Behavioral Therapy (CBT) framework with dynamic prompting that automatically adapts to the user's therapeutic progress.

---

## 🎯 핵심 기능 (Key Features)

### 1. 6단계 CBT 프레임워크

```
1단계: 초기 평가 (Assessment)
   ├─ 라포 형성 (Rapport building)
   ├─ 문제 파악 (Problem identification)
   └─ 목표 설정 (Goal establishment)

2단계: 재개념화 (Reconceptualization)
   ├─ ABC 모델 학습 (ABC model learning)
   ├─ 생각-감정-행동 연결고리 이해
   └─ 인지 왜곡 식별

3단계: 기술 습득 (Skills Acquisition)
   ├─ 인지 재구조화 (Cognitive restructuring)
   ├─ 문제 해결 기법
   └─ 행동 활성화

4단계: 기술 적용 (Skills Application)
   ├─ 실제 상황 적용
   ├─ 숙제 수행
   └─ 장애물 극복

5단계: 일반화 및 유지 (Generalization)
   ├─ 재발 방지 계획
   ├─ 자기 관리 전략
   └─ 장기 유지

6단계: 종결 (Termination)
   ├─ 성과 축하
   ├─ 미래 계획
   └─ 긍정적 종결
```

### 2. 동적 프롬프트 시스템

각 단계마다 고유한 시스템 프롬프트가 자동으로 적용됩니다:

- **단계별 프롬프트**: 각 단계당 500-2000+ 자의 상세한 한국어 가이드
- **실시간 진행도**: 현재 진행 상황이 프롬프트에 반영
- **목표 지향**: 각 단계의 특정 치료 목표 달성에 집중

### 3. 자동 진행도 평가

- **주기적 평가**: 3번의 메시지 교환마다 자동 평가
- **GPT-4 분석**: 최근 대화 내용을 GPT-4가 분석하여 진행도 측정
- **준비도 점수**: 다음 단계로의 전환 준비도 (0-100%)
- **권장사항**: continue, advance, review 등의 구체적 권장사항 제공

### 4. 단계 전환 로직

- **준비도 임계값**: 70% 이상일 때 다음 단계로 전환 가능
- **목표 추적**: 필수 vs 선택 목표 구분 관리
- **강제 전환**: 필요시 준비도와 무관하게 전환 가능
- **최종 단계 잠금**: 6단계(종결) 이후 전환 불가

### 5. 프론트엔드 통합

- **단계 인디케이터**: 현재 단계와 진행도를 시각적으로 표시
- **진행 바**: 0-100% 애니메이션 진행 바
- **목표 추적기**: 달성/진행 중인 목표 표시
- **준비도 배지**: 다음 단계 준비 시 표시

---

## 🏗️ 시스템 아키텍처

### Backend Architecture

```
┌─────────────────────────────────────────────────┐
│          Chat API (/chat/message)               │
│  - Initializes CBT stage for new conversations  │
│  - Uses CBT-aware completion                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         OpenAI Service                          │
│  chat_completion_with_cbt()                     │
│  - Gets dynamic prompt from CBT service         │
│  - Injects stage-aware prompt                   │
│  - Auto-assesses progress every 3 messages      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         CBT Stage Service                       │
│  - get_current_stage()                          │
│  - get_dynamic_prompt()                         │
│  - assess_stage_progress_auto()                 │
│  - transition_to_next_stage()                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         PostgreSQL Database                     │
│  - conversation_stages                          │
│  - stage_assessments                            │
│  - stage_milestones                             │
└─────────────────────────────────────────────────┘
```

### Frontend Architecture

```
┌─────────────────────────────────────────────────┐
│          ChatInterface Component                │
│  - Displays CBTStageIndicator                   │
│  - Manages conversation state                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│       CBTStageIndicator Component               │
│  - Shows current stage (1-6)                    │
│  - Displays progress bar                        │
│  - Shows goals achieved/pending                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│          useCBTStage Hook                       │
│  - Fetches stage data via API                   │
│  - Auto-refreshes every 30s                     │
│  - Manages loading/error states                 │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│          API Client (api-client.ts)             │
│  - getCBTStage()                                │
│  - getAllCBTStages()                            │
│  - getCBTStageInfo()                            │
└─────────────────────────────────────────────────┘
```

---

## 📊 데이터베이스 스키마

### conversation_stages 테이블

대화의 현재 CBT 단계와 진행 상황을 추적합니다.

```sql
CREATE TABLE conversation_stages (
    stage_id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(conversation_id),
    current_stage INTEGER CHECK (current_stage BETWEEN 1 AND 6),
    stage_name VARCHAR(50),
    stage_progress INTEGER CHECK (stage_progress BETWEEN 0 AND 100),
    goals_achieved JSONB DEFAULT '[]',
    goals_pending JSONB DEFAULT '[]',
    readiness_for_next_stage INTEGER CHECK (readiness_for_next_stage BETWEEN 0 AND 100),
    stage_history JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### stage_assessments 테이블

자동 진행도 평가 기록을 저장합니다.

```sql
CREATE TABLE stage_assessments (
    assessment_id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(conversation_id),
    stage INTEGER,
    stage_name VARCHAR(50),
    assessment_type VARCHAR(20),
    assessment_result JSONB,
    messages_analyzed INTEGER,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### stage_milestones 테이블

각 단계의 목표와 기준을 정의합니다.

```sql
CREATE TABLE stage_milestones (
    milestone_id UUID PRIMARY KEY,
    stage INTEGER,
    milestone_key VARCHAR(100),
    milestone_name VARCHAR(255),
    milestone_description TEXT,
    milestone_weight INTEGER DEFAULT 1,
    is_required BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**사전 입력된 마일스톤**: 6개 단계에 걸쳐 18개의 마일스톤이 사전 정의되어 있습니다.

---

## 🔌 API 엔드포인트

### 1. GET /cbt/stages/{conversation_id}

현재 CBT 단계와 진행 상황을 조회합니다.

**응답 예시**:
```json
{
  "success": true,
  "current_stage": {
    "stage_number": 2,
    "stage_name": "reconceptualization",
    "korean_name": "재개념화"
  },
  "progress": {
    "stage_progress": 65,
    "goals_achieved": ["abc_model_understood"],
    "goals_pending": ["identify_cognitive_distortions"],
    "readiness_for_next_stage": 60
  }
}
```

### 2. POST /cbt/stages/{conversation_id}/initialize

새 대화의 CBT 단계 추적을 초기화합니다 (1단계에서 시작).

### 3. POST /cbt/stages/{conversation_id}/assess

현재 단계의 진행도를 수동으로 평가합니다.

**요청 본문**:
```json
{
  "recent_messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### 4. POST /cbt/stages/{conversation_id}/advance

다음 단계로 전환합니다.

**쿼리 파라미터**:
- `force` (boolean): 준비도와 무관하게 강제 전환

### 5. GET /cbt/stages/{conversation_id}/history

단계 전환 이력을 조회합니다.

### 6. GET /cbt/stages/{conversation_id}/assessments

자동 평가 이력을 조회합니다.

### 7. GET /cbt/info/stages

전체 6개 단계의 정보를 조회합니다.

### 8. GET /cbt/info/stages/{stage_number}

특정 단계의 상세 정보를 조회합니다.

---

## 💻 사용 예시

### Backend - Dynamic Prompt Injection

```python
from app.services.cbt_stage_service import CBTStageService
from app.services.openai_service import OpenAIService

# Initialize services
cbt_service = CBTStageService(db=db, openai_client=openai_client)
openai_service = OpenAIService(cache_service=cache_service)

# Get CBT-aware response
response = await openai_service.chat_completion_with_cbt(
    messages=conversation_history,
    conversation_id=conv_id,
    cbt_service=cbt_service,
    redis_manager=redis,
    stream=True
)
```

### Frontend - Display Stage Information

```typescript
import CBTStageIndicator from '@/components/CBTStageIndicator'

function ChatInterface() {
  const [conversationId, setConversationId] = useState<string | null>(null)

  return (
    <div>
      {/* Show CBT stage indicator */}
      {conversationId && (
        <CBTStageIndicator conversationId={conversationId} />
      )}

      {/* Chat messages */}
      <MessageList messages={messages} />
    </div>
  )
}
```

### API Client - Fetch Stage Information

```typescript
import { getCBTStage, getAllCBTStages } from '@/lib/api-client'

// Get current stage for a conversation
const stageInfo = await getCBTStage(conversationId)
console.log(stageInfo.current_stage.korean_name) // "재개념화"
console.log(stageInfo.progress.stage_progress) // 65

// Get all stages information
const allStages = await getAllCBTStages()
console.log(allStages.stages.length) // 6
```

---

## 🧪 테스트

### Test Coverage

`backend/tests/test_cbt_stages.py`에 30개 이상의 포괄적인 테스트 케이스가 포함되어 있습니다:

#### 1. Enum Tests (3 tests)
- ✅ CBT 단계 enum 값 검증
- ✅ 단계 이름 및 한국어 이름 검증
- ✅ 단계 번호 정확성 검증

#### 2. Service Tests (10 tests)
- ✅ 단계 초기화
- ✅ 현재 단계 조회
- ✅ 진행도 조회
- ✅ 동적 프롬프트 생성
- ✅ 자동 진행도 평가
- ✅ 단계 전환 (성공/실패/강제)
- ✅ 최종 단계에서의 전환 방지

#### 3. API Endpoint Tests (8 tests)
- ✅ GET /cbt/stages/{conversation_id}
- ✅ POST /cbt/stages/{conversation_id}/initialize
- ✅ POST /cbt/stages/{conversation_id}/assess
- ✅ POST /cbt/stages/{conversation_id}/advance
- ✅ GET /cbt/stages/{conversation_id}/history
- ✅ GET /cbt/stages/{conversation_id}/assessments
- ✅ GET /cbt/info/stages
- ✅ GET /cbt/info/stages/{stage_number}

#### 4. Prompt Tests (4 tests)
- ✅ 모든 단계에 프롬프트 존재 확인
- ✅ 모든 단계에 목표 정의 확인
- ✅ 프롬프트에 한국어 포함 확인
- ✅ 프롬프트 구조 검증

#### 5. Integration Tests (2 tests)
- ✅ 전체 단계 진행 플로우
- ✅ 단계 목표 정렬

#### 6. Edge Case Tests (3 tests)
- ✅ 빈 메시지 목록으로 평가
- ✅ 존재하지 않는 대화 처리
- ✅ 잘못된 단계 번호 처리

### Running Tests

```bash
# Run all CBT tests
pytest backend/tests/test_cbt_stages.py -v

# Run with coverage
pytest backend/tests/test_cbt_stages.py --cov=app.services.cbt_stage_service --cov=app.api.cbt_stages

# Run specific test
pytest backend/tests/test_cbt_stages.py::test_cbt_stage_enum_values -v
```

---

## 📈 성능 및 최적화

### 자동 평가 빈도

- **빈도**: 3번의 메시지 교환마다
- **이유**: 너무 빈번한 평가는 API 비용 증가, 너무 드문 평가는 단계 전환 지연
- **최적화**: 메시지 카운터 기반 조건부 평가

### 캐싱 전략

- **단계 정보**: Redis에 캐싱 (5분 TTL)
- **마일스톤**: 앱 시작 시 메모리에 로드
- **프롬프트**: 서비스 클래스 레벨에서 정적으로 정의

### 데이터베이스 최적화

```sql
-- Indexes for fast queries
CREATE INDEX idx_conversation_stages_conversation ON conversation_stages(conversation_id);
CREATE INDEX idx_stage_assessments_conversation ON stage_assessments(conversation_id);
CREATE INDEX idx_stage_assessments_assessed_at ON stage_assessments(assessed_at DESC);
```

---

## 🔧 설정 및 커스터마이징

### 단계별 프롬프트 수정

`backend/app/services/cbt_stage_service.py`의 `STAGE_PROMPTS` 딕셔너리를 수정:

```python
STAGE_PROMPTS = {
    CBTStage.ASSESSMENT: """
    당신은 현재 **1단계: 초기 평가 (Assessment)** 단계에 있습니다.

    [프롬프트 내용 수정...]
    """,
    # ... 다른 단계들
}
```

### 단계 목표 수정

데이터베이스의 `stage_milestones` 테이블을 직접 수정하거나,
`database/migrations/006_add_cbt_stages.sql`의 마일스톤 삽입 부분을 수정:

```sql
INSERT INTO stage_milestones (stage, milestone_key, milestone_name, milestone_weight, is_required)
VALUES
    (1, 'rapport_built', '라포 형성', 3, true),
    (1, 'problem_identified', '문제 파악', 3, true);
    -- ... 더 추가
```

### 준비도 임계값 변경

`cbt_stage_service.py`의 `transition_to_next_stage` 메서드에서:

```python
READINESS_THRESHOLD = 70  # 기본값: 70%

if progress["readiness_for_next_stage"] < READINESS_THRESHOLD and not force:
    return {
        "success": False,
        "message": f"Not ready to advance. Readiness: {progress['readiness_for_next_stage']}%"
    }
```

### 자동 평가 빈도 조정

`openai_service.py`의 `chat_completion_with_cbt` 메서드에서:

```python
# 현재: 3번의 메시지마다 평가
if len(messages) % 3 == 0:
    await cbt_service.assess_stage_progress_auto(...)

# 변경 예: 5번의 메시지마다 평가
if len(messages) % 5 == 0:
    await cbt_service.assess_stage_progress_auto(...)
```

---

## 🚀 배포 체크리스트

### 1. 데이터베이스 마이그레이션

```bash
# CBT 테이블 생성
POSTGRES_PASSWORD=your_password ./database/run_migrations.sh
```

### 2. 환경 변수 확인

`.env` 파일에 필요한 변수가 설정되어 있는지 확인:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/mindful_counselor
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
```

### 3. 종속성 설치

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 4. 테스트 실행

```bash
# CBT 테스트
pytest backend/tests/test_cbt_stages.py -v

# 전체 테스트
pytest backend/tests/ --cov=app
```

### 5. 서비스 시작

```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

### 6. 동작 확인

```bash
# Health check
curl http://localhost:8000/health

# CBT stages info
curl http://localhost:8000/cbt/info/stages
```

---

## 📝 개발 로그

### 2024-11-05: 초기 구현

**구현된 기능**:
- ✅ 6단계 CBT 프레임워크
- ✅ 동적 프롬프트 시스템
- ✅ 자동 진행도 평가
- ✅ 8개 API 엔드포인트
- ✅ 프론트엔드 단계 인디케이터
- ✅ 포괄적인 테스트 스위트
- ✅ 완전한 문서화

**파일 변경 사항**:
- 새 파일 6개 (2,900+ 줄)
- 수정된 파일 6개
- 총 변경: 3,492 삽입, 15 삭제

**커밋**: `d4ed9a1` - "Implement comprehensive CBT 6-stage dynamic prompt system"

---

## 🔮 향후 개선 계획

### 단기 (1-2주)
- [ ] 단계별 시각화 차트 추가
- [ ] 목표 달성 알림 기능
- [ ] 진행도 리포트 생성
- [ ] 단계 전환 애니메이션

### 중기 (1-2개월)
- [ ] 머신러닝 기반 준비도 예측
- [ ] 개인화된 단계 속도 조절
- [ ] 단계별 성공률 분석
- [ ] A/B 테스트 프레임워크

### 장기 (3-6개월)
- [ ] 다른 치료 모델 통합 (ACT, DBT)
- [ ] 다국어 프롬프트 지원
- [ ] 상담사 대시보드
- [ ] 실시간 진행도 공유

---

## 🤝 기여 가이드

CBT 시스템 개선에 기여하고 싶으시면:

1. 이슈 생성하여 제안 사항 논의
2. 포크 후 브랜치 생성 (`feature/cbt-improvement`)
3. 변경 사항 구현 및 테스트 추가
4. PR 제출 with 상세한 설명

---

## 📚 참고 자료

### CBT 이론
- Beck, J. S. (2011). *Cognitive Behavior Therapy: Basics and Beyond*
- Wright, J. H., et al. (2017). *Computer-Assisted Cognitive Therapy*

### 구현 참고
- OpenAI GPT-4 Documentation
- FastAPI Documentation
- PostgreSQL JSONB Documentation
- React Hooks Best Practices

---

## 📞 지원

문제가 발생하거나 질문이 있으시면:

- **GitHub Issues**: [프로젝트 이슈 트래커]
- **문서**: `/docs/API.md`에서 전체 API 문서 확인
- **테스트**: `backend/tests/test_cbt_stages.py`에서 예시 코드 확인

---

**최종 업데이트**: 2024-11-05
**버전**: 1.0.0
**상태**: ✅ 프로덕션 준비 완료
