# Dynamic Prompt Switching System
# 동적 프롬프트 전환 시스템

**Version:** 1.0.0
**Date:** 2025-11-05
**Author:** AI Counselor Development Team

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Prompt Selection Logic](#prompt-selection-logic)
4. [Prompt Library](#prompt-library)
5. [Emotion Detection](#emotion-detection)
6. [API Reference](#api-reference)
7. [Integration Guide](#integration-guide)
8. [Testing](#testing)
9. [Performance](#performance)

---

## Overview

### Purpose

The **Dynamic Prompt Switching System** (동적 프롬프트 전환 시스템) is an intelligent system that automatically selects the most appropriate counseling prompt based on multiple real-time factors:

1. **Crisis Level** (최우선 순위) - C-SSRS Level 0-4
2. **Age Group** - Adolescent (13-18) vs Adult (19+)
3. **CBT Stage** - 6 therapeutic stages
4. **Emotional State** - Detected emotion and intensity
5. **Conversation Context** - Message history and patterns

### Key Benefits

✅ **Contextually Appropriate Responses** - Each prompt is tailored to the specific situation
✅ **Safety First** - Crisis situations trigger immediate intervention prompts
✅ **Developmentally Appropriate** - Teen vs adult communication styles
✅ **Stage-Aware Therapy** - CBT progression is respected
✅ **Emotion-Sensitive** - Responds appropriately to emotional states

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHAT COMPLETION REQUEST                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              DYNAMIC PROMPT SERVICE                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. CRISIS DETECTION (Highest Priority)                  │   │
│  │     - EnhancedCrisisDetectionSystem                      │   │
│  │     - C-SSRS Level 3-4 → Crisis Intervention Prompt     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  2. CONTEXT ANALYSIS                                     │   │
│  │     - Age Group (from user profile)                      │   │
│  │     - CBT Stage (from conversation state)                │   │
│  │     - Emotion Detection (from last message)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  3. PROMPT SELECTION                                     │   │
│  │     - Build prompt key: AGE_STAGE_EMOTION                │   │
│  │     - Retrieve from PromptLibrary                        │   │
│  │     - Fallback to default if not found                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              SELECTED PROMPT + MESSAGES → OpenAI API             │
└─────────────────────────────────────────────────────────────────┘
```

### Core Classes

#### 1. `DynamicPromptService`
- **Location:** `backend/app/services/dynamic_prompt_service.py`
- **Responsibility:** Orchestrates prompt selection logic
- **Key Methods:**
  - `select_prompt()` - Main selection algorithm
  - `_build_prompt_key()` - Constructs prompt identifier
  - `_get_prompt_from_library()` - Retrieves prompt with fallback

#### 2. `PromptLibrary`
- **Location:** `backend/app/services/dynamic_prompt_service.py`
- **Responsibility:** Stores all counseling prompts
- **Prompts:** 12+ specialized prompts covering all scenarios
- **Format:** Korean language, 300-700 lines per prompt

#### 3. `EmotionDetector`
- **Location:** `backend/app/services/dynamic_prompt_service.py`
- **Responsibility:** Detects emotion and intensity from text
- **Method:** Keyword-based pattern matching
- **Emotions:** Anxiety, Depression, Anger, Fear, Sadness, Shame, Guilt, Joy, Neutral

---

## Prompt Selection Logic

### Priority Hierarchy

```python
def select_prompt(conversation_context):
    # PRIORITY 1: Crisis Detection (OVERRIDE ALL)
    if crisis_level >= 3:
        return CRISIS_INTERVENTION_PROMPT

    # PRIORITY 2: Multi-factor Selection
    # - Age Group (Teen vs Adult)
    # - CBT Stage (1-6)
    # - Emotion (9 types)

    prompt_key = f"{age_group}_{cbt_stage}_{emotion}"
    return PROMPT_LIBRARY[prompt_key]
```

### Prompt Key Construction

**Format:** `{AGE}_{STAGE}_{EMOTION}`

**Examples:**
- `TEEN_ASSESSMENT_ANXIETY` - Anxious adolescent in first session
- `ADULT_SKILLS_DEPRESSION` - Depressed adult learning CBT techniques
- `TEEN_APPLICATION_ANGER` - Angry teen applying anger management skills
- `ADULT_MAINTENANCE_NEUTRAL` - Stable adult in maintenance phase

### Fallback Logic

```
1. Try exact match: TEEN_SKILLS_ANXIETY
2. If not found, try related: TEEN_ASSESSMENT_ANXIETY
3. If not found, use: DEFAULT_GENERAL
```

---

## Prompt Library

### Complete Prompt Inventory

| Key | Age | Stage | Emotion | Description |
|-----|-----|-------|---------|-------------|
| **CRISIS_INTERVENTION** | All | All | Crisis | 자살/자해 위험 긴급 개입 |
| **TEEN_ASSESSMENT_ANXIETY** | 청소년 | 1단계 | 불안 | 불안한 청소년 초기 평가 |
| **TEEN_ASSESSMENT_DEPRESSION** | 청소년 | 1단계 | 우울 | 우울한 청소년 첫 만남 |
| **TEEN_RECONCEPTUALIZATION_DEPRESSION** | 청소년 | 2단계 | 우울 | 우울 청소년 문제 재정의 |
| **TEEN_SKILLS_ANXIETY** | 청소년 | 3단계 | 불안 | 불안 관리 기법 교육 |
| **TEEN_APPLICATION_ANGER** | 청소년 | 4단계 | 분노 | 분노 관리 실전 적용 |
| **ADULT_ASSESSMENT_ANXIETY** | 성인 | 1단계 | 불안 | 불안 증상 초기 평가 |
| **ADULT_RECONCEPTUALIZATION_DEPRESSION** | 성인 | 2단계 | 우울 | 우울의 CBT 개념화 |
| **ADULT_SKILLS_DEPRESSION** | 성인 | 3단계 | 우울 | 인지 재구조화 기법 교육 |
| **ADULT_APPLICATION_ANXIETY** | 성인 | 4단계 | 불안 | 노출 치료 실전 적용 |
| **ADULT_MAINTENANCE_NEUTRAL** | 성인 | 5-6단계 | 안정 | 재발 방지 및 종결 준비 |
| **DEFAULT_GENERAL** | All | All | All | 일반 상담 폴백 프롬프트 |

### Prompt Structure

Each prompt follows this structure:

```
1. Identity & Context
   - Who you are (청소년/성인 전문 상담사)
   - Current stage (초기 평가/기술 습득/등)
   - Client's emotional state (불안/우울/분노)

2. Approach Guidelines
   - Age-appropriate communication style
   - Stage-specific therapeutic goals
   - Emotion-specific techniques

3. Concrete Examples
   - Question styles
   - Response templates
   - Language samples

4. What to Avoid
   - Common mistakes
   - Contraindicated approaches
   - Potential harm

5. Closing Directive
   - Summary of mission
   - Final encouragement
```

### Sample Prompt Excerpt

**TEEN_ASSESSMENT_ANXIETY (청소년 초기평가 - 불안)**

```
당신은 청소년 전문 심리상담사입니다. 지금은 **첫 만남** 단계이고,
내담자는 **불안**을 느끼고 있습니다.

**청소년 특화 접근:**
- 친근하고 편안한 톤 사용 (존댓말 but 격식 줄이기)
- 짧고 명확한 문장 (한 번에 1-2개 질문만)
- 학교/친구 관계 중심 공감
- "너"보다 "네가", "자네"보다 "너" 같은 자연스러운 표현

**상담 목표:**
1. 라포 형성 - 안전한 공간 느끼게 하기
2. 불안의 구체적 상황 파악
3. 청소년의 강점 찾기
4. 판단하지 않는 태도 명확히 하기

**질문 스타일:**
- 열린 질문: "요즘 어떤 일로 가장 걱정돼?"
- 구체화: "학교에서 특히 언제 그런 느낌이 들어?"
- 정상화: "많은 친구들이 비슷한 고민을 하더라"

**피해야 할 것:**
- 부모처럼 훈계하기
- 해결책 급하게 제시하기
- 청소년의 감정을 과소평가하기
- 너무 많은 질문 쏟아내기

청소년이 편안하게 자신의 이야기를 꺼낼 수 있도록 이끌어주세요.
```

---

## Emotion Detection

### Detection Method

The `EmotionDetector` uses **keyword-based pattern matching** with intensity levels:

```python
EMOTION_KEYWORDS = {
    EmotionType.ANXIETY: {
        "high": ["극도로 불안", "패닉", "공황", "너무 불안"],
        "moderate": ["불안", "걱정", "초조", "긴장"],
        "low": ["약간 걱정", "좀 불안"]
    },
    # ... more emotions
}
```

### Emotion Types

| Emotion | Korean | Example Keywords |
|---------|--------|------------------|
| ANXIETY | 불안 | 불안, 걱정, 초조, 긴장, 공황 |
| DEPRESSION | 우울 | 우울, 무기력, 의욕 없음, 희망 없음 |
| ANGER | 분노 | 화나, 짜증, 열받아, 분노 |
| FEAR | 두려움 | 무서워, 두려워, 겁나 |
| SADNESS | 슬픔 | 슬프, 서러워, 눈물 |
| SHAME | 수치심 | 부끄러워, 창피해, 수치스러워 |
| GUILT | 죄책감 | 죄책감, 미안해, 후회돼 |
| JOY | 기쁨 | 기뻐, 좋아, 행복해 |
| NEUTRAL | 중립 | (no keywords) |

### Intensity Scoring

- **High (7-10):** 극도로, 너무, 매우 + emotion
- **Moderate (4-6):** Basic emotion words
- **Low (1-3):** 약간, 좀 + emotion

### Emotion Detection Example

```python
# Input
message = "학교 가는 게 너무 불안하고 공황 올 것 같아요"

# Output
emotion = EmotionType.ANXIETY
intensity = EmotionIntensity.EXTREME (9)
```

---

## API Reference

### Base URL

```
/api/prompts
```

### Endpoints

#### 1. Select Optimal Prompt

**POST** `/prompts/select`

Intelligently selects the best prompt based on conversation context.

**Request:**
```json
{
  "last_message": "요즘 너무 불안해서 잠을 못 자요",
  "user_age": 16,
  "cbt_stage": 1,
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "selected_prompt": "당신은 청소년 전문 심리상담사입니다...",
  "prompt_key": "TEEN_ASSESSMENT_ANXIETY",
  "factors": {
    "crisis_level": 0,
    "age_group": "adolescent",
    "cbt_stage": 1,
    "emotion": "anxiety",
    "intensity": 7
  },
  "reasoning": "청소년 내담자 + 초기 평가 단계 + 불안 감정 (강도 높음)에 최적화된 프롬프트 선택",
  "metadata": {
    "timestamp": "2025-11-05T10:30:00",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_age": 16,
    "prompt_length": 1542
  }
}
```

#### 2. Detect Emotion

**POST** `/prompts/detect-emotion`

Analyzes message text to detect primary emotion and intensity.

**Request:**
```json
{
  "message": "너무 불안하고 걱정돼서 미칠 것 같아요"
}
```

**Response:**
```json
{
  "emotion": "anxiety",
  "intensity": 9,
  "emotion_label_ko": "불안",
  "intensity_label": "매우 높음",
  "confidence": 0.9
}
```

#### 3. Get Prompt Library

**GET** `/prompts/library`

Returns metadata for all available prompts.

**Response:**
```json
{
  "available_prompts": [
    {
      "key": "CRISIS_INTERVENTION",
      "name_ko": "위기 개입 프롬프트",
      "description": "자살/자해 위험 상태 내담자를 위한 긴급 개입 프롬프트",
      "target_crisis_level": "3-4",
      "target_age": "모든 연령",
      "target_stage": "모든 단계",
      "priority": "최우선"
    },
    // ... more prompts
  ],
  "total_count": 12
}
```

#### 4. Get Prompt by Key

**GET** `/prompts/library/{prompt_key}`

Retrieves the full text of a specific prompt.

**Example:**
```
GET /prompts/library/TEEN_ASSESSMENT_ANXIETY
```

**Response:**
```json
{
  "prompt_key": "TEEN_ASSESSMENT_ANXIETY",
  "prompt_text": "당신은 청소년 전문 심리상담사입니다...",
  "length": 1542,
  "lines": 42
}
```

#### 5. Test Scenarios

**POST** `/prompts/test-scenarios`

Runs predefined test scenarios to verify prompt selection logic.

**Response:**
```json
{
  "total_scenarios": 7,
  "results": [
    {
      "scenario": "위기 상황 - 자살 의도",
      "input": {
        "message": "더 이상 살고 싶지 않아요. 유서도 써뒀어요.",
        "age": 25,
        "stage": 1
      },
      "output": {
        "prompt_key": "CRISIS_INTERVENTION",
        "reasoning": "Crisis level 4 detected - immediate intervention required",
        "factors": {
          "crisis_level": 4,
          "age_group": "adult",
          "cbt_stage": 1,
          "emotion": "crisis",
          "intensity": 10
        },
        "prompt_preview": "당신은 위기 개입 전문 심리상담사입니다..."
      }
    }
    // ... more scenarios
  ],
  "timestamp": "2025-11-05T10:30:00"
}
```

#### 6. Get Emotion Keywords

**GET** `/prompts/emotions/keywords`

Returns the emotion detection keyword dictionary.

**Response:**
```json
{
  "emotion_keywords": {
    "anxiety": {
      "high": ["극도로 불안", "패닉", "공황"],
      "moderate": ["불안", "걱정", "초조"],
      "low": ["약간 걱정", "좀 불안"]
    }
    // ... more emotions
  },
  "available_emotions": ["anxiety", "depression", "anger", ...],
  "intensity_levels": {
    "high": "7-10 (극도, 매우 높음)",
    "moderate": "4-6 (보통)",
    "low": "1-3 (낮음, 최소)"
  }
}
```

---

## Integration Guide

### Using in Chat API

The dynamic prompt system is integrated via the `chat_completion_with_dynamic_prompts` method in `OpenAIService`.

**Example Integration:**

```python
from app.services.openai_service import OpenAIService
from app.services.cbt_stage_service import CBTStageService
from app.services.dynamic_prompt_service import DynamicPromptService

# Initialize services
openai_service = OpenAIService(cache_service=cache)
cbt_service = CBTStageService(db=db, openai_client=openai_service.client)
dynamic_prompt_service = DynamicPromptService(openai_client=openai_service.client)

# Generate response with dynamic prompts
response = await openai_service.chat_completion_with_dynamic_prompts(
    messages=conversation_messages,
    conversation_id=str(conversation.id),
    cbt_service=cbt_service,
    dynamic_prompt_service=dynamic_prompt_service,
    redis_manager=redis,
    user_age=user.age,  # From user profile
    stream=False,
    user_id=str(user.id)
)
```

### System Flow

1. **User sends message** → Chat API receives request
2. **FAQ check** → Check for common questions (fast path)
3. **Dynamic prompt selection:**
   - Detect crisis level (C-SSRS)
   - Determine age group from user profile
   - Get current CBT stage from conversation
   - Detect emotion from last message
   - Select optimal prompt
4. **Inject prompt** → Add as system message to conversation
5. **Semantic cache check** → Check for similar recent queries
6. **OpenAI API call** → Generate response with selected prompt
7. **Cache & track** → Cache response and track usage
8. **Auto-assessment** → Every 3 messages, assess CBT progress

---

## Testing

### Manual Testing

Use the test scenarios endpoint:

```bash
curl -X POST http://localhost:8000/api/prompts/test-scenarios
```

This runs 7 predefined scenarios covering:
1. Crisis situation (suicide ideation)
2. Teen anxiety - assessment
3. Teen depression - assessment
4. Teen anger - application
5. Adult depression - skills
6. Adult anxiety - application
7. Adult stable - maintenance

### Expected Results

Each test should:
- ✅ Select the correct prompt key
- ✅ Provide clear reasoning
- ✅ Show all factor values
- ✅ Respect priority hierarchy (crisis > age > stage > emotion)

### Example Test Result

```json
{
  "scenario": "청소년 불안 - 초기 평가",
  "input": {
    "message": "학교 가는 게 너무 불안하고 걱정돼요",
    "age": 15,
    "stage": 1
  },
  "output": {
    "prompt_key": "TEEN_ASSESSMENT_ANXIETY",
    "reasoning": "청소년 내담자 + 초기 평가 단계 + 불안 감정에 최적화된 프롬프트 선택",
    "factors": {
      "crisis_level": 0,
      "age_group": "adolescent",
      "cbt_stage": 1,
      "emotion": "anxiety",
      "intensity": 7
    }
  }
}
```

### Unit Testing

Create unit tests for:

1. **Emotion Detection**
   ```python
   def test_emotion_detection():
       detector = EmotionDetector()
       emotion, intensity = detector.detect_emotion("너무 불안해요")
       assert emotion == EmotionType.ANXIETY
       assert intensity >= EmotionIntensity.HIGH
   ```

2. **Prompt Selection**
   ```python
   async def test_prompt_selection_crisis():
       service = DynamicPromptService()
       result = await service.select_prompt(
           conversation_context={"messages": [...]},
           crisis_level=CSSRSLevel.LEVEL_4_IMMINENT
       )
       assert result["prompt_key"] == "CRISIS_INTERVENTION"
   ```

3. **Fallback Logic**
   ```python
   def test_prompt_fallback():
       service = DynamicPromptService()
       prompt = service._get_prompt_from_library("NONEXISTENT_KEY")
       assert prompt == service.prompt_library.DEFAULT_GENERAL
   ```

---

## Performance

### Computational Complexity

**Emotion Detection:** O(n × m)
- n = message length
- m = number of keywords per emotion
- Typical: < 1ms for 1000-character messages

**Prompt Selection:** O(1)
- Dictionary lookup
- Typical: < 0.1ms

**Total Overhead:** 1-2ms per request (negligible)

### Memory Usage

- **Prompt Library:** ~150KB (12 prompts × ~12KB each)
- **Keyword Dictionary:** ~5KB
- **Total Service Footprint:** ~200KB

All prompts are loaded once at startup and kept in memory.

### Caching Strategy

The system benefits from existing caching layers:

1. **FAQ Cache** - Common questions answered instantly
2. **Semantic Cache** - Similar conversations reuse responses
3. **Prompt Selection** - No caching needed (already O(1))

### Scalability

**Concurrent Requests:** Unlimited (stateless service)
**Database Impact:** None (no DB queries)
**External API Calls:** Only OpenAI (for crisis detection)

---

## Troubleshooting

### Common Issues

#### Issue 1: Wrong prompt selected

**Symptom:** Prompt doesn't match expected scenario

**Diagnosis:**
```bash
# Check prompt selection reasoning
curl -X POST http://localhost:8000/api/prompts/select \
  -H "Content-Type: application/json" \
  -d '{"last_message": "...", "user_age": 16, "cbt_stage": 1}'
```

**Solution:** Verify factors in response - check age_group, cbt_stage, emotion

#### Issue 2: Emotion not detected

**Symptom:** Emotion shows as "neutral" when it shouldn't

**Diagnosis:**
```bash
# Test emotion detection directly
curl -X POST http://localhost:8000/api/prompts/detect-emotion \
  -H "Content-Type: application/json" \
  -d '{"message": "너무 불안해요"}'
```

**Solution:** Add missing keywords to `EMOTION_KEYWORDS` dictionary

#### Issue 3: Crisis not triggering

**Symptom:** Crisis message doesn't get CRISIS_INTERVENTION prompt

**Diagnosis:** Check C-SSRS detection logs

**Solution:** Ensure `EnhancedCrisisDetectionSystem` is working correctly

---

## Future Enhancements

### Planned Features

1. **GPT-4 Emotion Detection** (현재 keyword 기반 → AI 기반)
   - More accurate emotion analysis
   - Context-aware intensity scoring
   - Multi-emotion detection

2. **Personalized Prompts** (개인화 프롬프트)
   - Learn from user preferences
   - Adapt tone over time
   - Cultural/regional variations

3. **Prompt A/B Testing** (프롬프트 A/B 테스트)
   - Compare prompt effectiveness
   - Optimize based on outcomes
   - User satisfaction metrics

4. **Multi-language Support** (다국어 지원)
   - English prompts
   - Other languages
   - Automatic translation

5. **Advanced Stage Detection** (고급 단계 탐지)
   - ML-based stage prediction
   - Automatic progression
   - Regression detection

---

## Appendix

### Glossary

- **CBT (Cognitive Behavioral Therapy):** 인지행동치료
- **C-SSRS:** Columbia Suicide Severity Rating Scale
- **ASQ:** Ask Suicide-Screening Questions
- **Prompt:** System instruction for AI model
- **System Message:** Role definition for AI
- **Dynamic Prompting:** Context-aware prompt selection
- **Fallback:** Default option when primary fails

### References

1. Beck, A. T. (1979). *Cognitive Therapy and the Emotional Disorders*
2. Columbia Lighthouse Project. (2016). *C-SSRS Screening Version*
3. Horowitz, L. M., et al. (2012). *Ask Suicide-Screening Questions (ASQ)*
4. Korean Association of CBT. (2023). *CBT Practice Guidelines*

### Related Documentation

- [CBT System Documentation](./CBT_SYSTEM.md)
- [Crisis Detection Enhanced](./CRISIS_DETECTION_ENHANCED.md)
- [Age-Based Counseling](./AGE_BASED_COUNSELING.md)

---

**End of Documentation**

For questions or support, contact the development team.
