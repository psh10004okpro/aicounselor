"""
Dynamic Prompt API Endpoints
동적 프롬프트 API

Provides endpoints for testing and using the dynamic prompt selection system.

Author: AI Counselor System
Date: 2025-11-05
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.dynamic_prompt_service import (
    DynamicPromptService,
    EmotionType,
    EmotionIntensity,
    SpecialSituation
)
from app.services.crisis_detector_enhanced import CSSRSLevel
from app.services.age_based_counseling import AgeGroup
from app.services.cbt_stage_service import CBTStage, CBTStageService
from app.services.openai_service import OpenAIService


router = APIRouter(prefix="/api", tags=["dynamic-prompts"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PromptSelectionRequest(BaseModel):
    """Request for prompt selection"""
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    last_message: str = Field(..., description="Most recent user message")
    user_age: Optional[int] = Field(None, description="User age (for age group determination)")
    crisis_level: Optional[int] = Field(None, description="C-SSRS level (0-4)")
    cbt_stage: Optional[int] = Field(None, description="CBT stage (1-6)")
    force_emotion: Optional[str] = Field(None, description="Force specific emotion type for testing")


class EmotionDetectionRequest(BaseModel):
    """Request for emotion detection only"""
    message: str = Field(..., description="Message text to analyze")


class EmotionDetectionResponse(BaseModel):
    """Response for emotion detection"""
    emotion: str
    intensity: int
    emotion_label_ko: str
    intensity_label: str
    confidence: float


class PromptSelectionResponse(BaseModel):
    """Response for prompt selection"""
    selected_prompt: str
    prompt_key: str
    factors: Dict
    reasoning: str
    metadata: Dict


class PromptLibraryResponse(BaseModel):
    """Response for prompt library listing"""
    available_prompts: List[Dict]
    total_count: int


# ============================================================================
# Helper Functions
# ============================================================================

def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance"""
    return OpenAIService()


def get_dynamic_prompt_service(
    openai_service: OpenAIService = Depends(get_openai_service)
) -> DynamicPromptService:
    """Get dynamic prompt service instance"""
    return DynamicPromptService(openai_client=openai_service.client)


def get_emotion_label_ko(emotion: EmotionType) -> str:
    """Get Korean label for emotion"""
    labels = {
        EmotionType.ANXIETY: "불안",
        EmotionType.DEPRESSION: "우울",
        EmotionType.ANGER: "분노",
        EmotionType.FEAR: "두려움",
        EmotionType.SADNESS: "슬픔",
        EmotionType.NEUTRAL: "중립",
        EmotionType.JOY: "기쁨",
        EmotionType.SHAME: "수치심",
        EmotionType.GUILT: "죄책감"
    }
    return labels.get(emotion, "알 수 없음")


def get_intensity_label(intensity: EmotionIntensity) -> str:
    """Get label for intensity"""
    if intensity >= 9:
        return "매우 높음"
    elif intensity >= 7:
        return "높음"
    elif intensity >= 5:
        return "보통"
    elif intensity >= 3:
        return "낮음"
    else:
        return "최소"


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/prompts/select", response_model=PromptSelectionResponse)
async def select_prompt(
    request: PromptSelectionRequest,
    db: AsyncSession = Depends(get_db),
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service),
    cbt_service: CBTStageService = Depends()
):
    """
    Select optimal prompt based on conversation context

    대화 맥락을 기반으로 최적의 프롬프트 선택

    **Priority Logic:**
    1. Crisis level 3-4 → Crisis intervention prompt
    2. Age + CBT stage + Emotion → Specific targeted prompt
    3. Default general counseling prompt

    **Example:**
    ```json
    {
        "last_message": "요즘 너무 불안해서 잠을 못 자요",
        "user_age": 16,
        "cbt_stage": 1
    }
    ```
    """
    try:
        # Determine age group
        age_group = None
        if request.user_age:
            if 13 <= request.user_age <= 18:
                age_group = AgeGroup.ADOLESCENT
            elif request.user_age >= 19:
                age_group = AgeGroup.ADULT

        # Get CBT stage if conversation_id provided
        cbt_stage = None
        if request.conversation_id:
            try:
                stage_info = await cbt_service.get_current_stage(request.conversation_id)
                if stage_info:
                    cbt_stage = stage_info
            except:
                pass

        # Override with explicit cbt_stage if provided
        if request.cbt_stage:
            cbt_stage = CBTStage(request.cbt_stage)

        # Convert crisis level to enum
        crisis_level = None
        if request.crisis_level is not None:
            crisis_level = CSSRSLevel(request.crisis_level)

        # Build conversation context
        conversation_context = {
            "messages": [{"content": request.last_message, "role": "user"}],
            "user_age_group": age_group.value if age_group else None
        }

        # Select prompt
        result = await prompt_service.select_prompt(
            conversation_context=conversation_context,
            crisis_level=crisis_level,
            age_group=age_group,
            cbt_stage=cbt_stage,
            last_message=request.last_message
        )

        # Add metadata
        result["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": request.conversation_id,
            "user_age": request.user_age,
            "prompt_length": len(result["selected_prompt"])
        }

        return PromptSelectionResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt selection failed: {str(e)}")


@router.post("/prompts/detect-emotion", response_model=EmotionDetectionResponse)
async def detect_emotion(
    request: EmotionDetectionRequest,
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service)
):
    """
    Detect emotion and intensity from message text

    메시지 텍스트에서 감정과 강도 탐지

    **Example:**
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
        "intensity_label": "매우 높음"
    }
    ```
    """
    try:
        emotion, intensity = prompt_service.emotion_detector.detect_emotion(request.message)

        # Calculate confidence (simplified)
        confidence = min(intensity / 10.0, 1.0)

        return EmotionDetectionResponse(
            emotion=emotion.value,
            intensity=intensity,
            emotion_label_ko=get_emotion_label_ko(emotion),
            intensity_label=get_intensity_label(intensity),
            confidence=confidence
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion detection failed: {str(e)}")


@router.get("/prompts/library", response_model=PromptLibraryResponse)
async def get_prompt_library():
    """
    Get list of all available prompts in the library

    프롬프트 라이브러리의 모든 사용 가능한 프롬프트 목록 조회

    **Returns:**
    List of prompt metadata including keys, descriptions, and target scenarios
    """
    prompts = [
        {
            "key": "CRISIS_INTERVENTION",
            "name_ko": "위기 개입 프롬프트",
            "description": "자살/자해 위험 상태 내담자를 위한 긴급 개입 프롬프트",
            "target_crisis_level": "3-4",
            "target_age": "모든 연령",
            "target_stage": "모든 단계",
            "priority": "최우선"
        },
        {
            "key": "TEEN_ASSESSMENT_ANXIETY",
            "name_ko": "청소년 초기평가 - 불안",
            "description": "불안을 느끼는 청소년의 첫 상담 세션",
            "target_age": "청소년 (13-18세)",
            "target_stage": "1단계: 초기 평가",
            "target_emotion": "불안"
        },
        {
            "key": "TEEN_ASSESSMENT_DEPRESSION",
            "name_ko": "청소년 초기평가 - 우울",
            "description": "우울감을 느끼는 청소년의 첫 상담 세션",
            "target_age": "청소년 (13-18세)",
            "target_stage": "1단계: 초기 평가",
            "target_emotion": "우울"
        },
        {
            "key": "TEEN_RECONCEPTUALIZATION_DEPRESSION",
            "name_ko": "청소년 재개념화 - 우울",
            "description": "우울한 청소년의 문제 재정의 단계",
            "target_age": "청소년 (13-18세)",
            "target_stage": "2단계: 재개념화",
            "target_emotion": "우울"
        },
        {
            "key": "TEEN_SKILLS_ANXIETY",
            "name_ko": "청소년 기술습득 - 불안",
            "description": "불안 관리 기법을 배우는 청소년",
            "target_age": "청소년 (13-18세)",
            "target_stage": "3단계: 기술 습득",
            "target_emotion": "불안"
        },
        {
            "key": "TEEN_APPLICATION_ANGER",
            "name_ko": "청소년 기술적용 - 분노",
            "description": "분노 관리 기법을 실생활에 적용하는 청소년",
            "target_age": "청소년 (13-18세)",
            "target_stage": "4단계: 기술 적용",
            "target_emotion": "분노"
        },
        {
            "key": "ADULT_ASSESSMENT_ANXIETY",
            "name_ko": "성인 초기평가 - 불안",
            "description": "불안 증상을 호소하는 성인의 초기 평가",
            "target_age": "성인 (19세 이상)",
            "target_stage": "1단계: 초기 평가",
            "target_emotion": "불안"
        },
        {
            "key": "ADULT_RECONCEPTUALIZATION_DEPRESSION",
            "name_ko": "성인 재개념화 - 우울",
            "description": "우울 증상의 CBT 개념화 단계",
            "target_age": "성인 (19세 이상)",
            "target_stage": "2단계: 재개념화",
            "target_emotion": "우울"
        },
        {
            "key": "ADULT_SKILLS_DEPRESSION",
            "name_ko": "성인 기술습득 - 우울",
            "description": "우울 관리 CBT 기법 교육",
            "target_age": "성인 (19세 이상)",
            "target_stage": "3단계: 기술 습득",
            "target_emotion": "우울"
        },
        {
            "key": "ADULT_APPLICATION_ANXIETY",
            "name_ko": "성인 기술적용 - 불안",
            "description": "불안 관리 기법 실전 적용 및 노출 치료",
            "target_age": "성인 (19세 이상)",
            "target_stage": "4단계: 기술 적용",
            "target_emotion": "불안"
        },
        {
            "key": "ADULT_MAINTENANCE_NEUTRAL",
            "name_ko": "성인 유지관리 - 안정",
            "description": "치료 종결 준비 및 재발 방지",
            "target_age": "성인 (19세 이상)",
            "target_stage": "5-6단계: 유지 및 종결",
            "target_emotion": "중립/안정"
        },
        {
            "key": "DEFAULT_GENERAL",
            "name_ko": "일반 상담 프롬프트",
            "description": "기본 심리상담 프롬프트 (폴백)",
            "target_age": "모든 연령",
            "target_stage": "모든 단계",
            "target_emotion": "모든 감정"
        }
    ]

    return PromptLibraryResponse(
        available_prompts=prompts,
        total_count=len(prompts)
    )


@router.get("/prompts/library/{prompt_key}")
async def get_prompt_by_key(
    prompt_key: str,
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service)
):
    """
    Get specific prompt text by key

    키로 특정 프롬프트 텍스트 조회

    **Available keys:**
    - CRISIS_INTERVENTION
    - TEEN_ASSESSMENT_ANXIETY
    - TEEN_ASSESSMENT_DEPRESSION
    - TEEN_RECONCEPTUALIZATION_DEPRESSION
    - TEEN_SKILLS_ANXIETY
    - TEEN_APPLICATION_ANGER
    - ADULT_ASSESSMENT_ANXIETY
    - ADULT_RECONCEPTUALIZATION_DEPRESSION
    - ADULT_SKILLS_DEPRESSION
    - ADULT_APPLICATION_ANXIETY
    - ADULT_MAINTENANCE_NEUTRAL
    - DEFAULT_GENERAL
    """
    try:
        prompt_text = getattr(prompt_service.prompt_library, prompt_key, None)

        if prompt_text is None:
            raise HTTPException(status_code=404, detail=f"Prompt key '{prompt_key}' not found")

        return {
            "prompt_key": prompt_key,
            "prompt_text": prompt_text,
            "length": len(prompt_text),
            "lines": prompt_text.count('\n') + 1
        }

    except AttributeError:
        raise HTTPException(status_code=404, detail=f"Prompt key '{prompt_key}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve prompt: {str(e)}")


@router.post("/prompts/test-scenarios")
async def test_prompt_scenarios(
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service)
):
    """
    Test dynamic prompt selection with predefined scenarios

    사전 정의된 시나리오로 동적 프롬프트 선택 테스트

    **Returns:**
    Results for multiple test scenarios showing prompt selection logic
    """
    test_scenarios = [
        {
            "name": "위기 상황 - 자살 의도",
            "last_message": "더 이상 살고 싶지 않아요. 유서도 써뒀어요.",
            "user_age": 25,
            "cbt_stage": 1
        },
        {
            "name": "청소년 불안 - 초기 평가",
            "last_message": "학교 가는 게 너무 불안하고 걱정돼요",
            "user_age": 15,
            "cbt_stage": 1
        },
        {
            "name": "청소년 우울 - 초기 평가",
            "last_message": "요즘 아무것도 재미없고 다 귀찮아요",
            "user_age": 17,
            "cbt_stage": 1
        },
        {
            "name": "청소년 분노 - 기술 적용",
            "last_message": "친구가 너무 화나. 때리고 싶어",
            "user_age": 16,
            "cbt_stage": 4
        },
        {
            "name": "성인 우울 - 기술 습득",
            "last_message": "계속 부정적인 생각만 들어요. 어떻게 바꿔야 할까요?",
            "user_age": 32,
            "cbt_stage": 3
        },
        {
            "name": "성인 불안 - 기술 적용",
            "last_message": "발표 앞두고 너무 불안해요. 배운 기법을 써보려는데 잘 안돼요",
            "user_age": 28,
            "cbt_stage": 4
        },
        {
            "name": "성인 안정 - 유지 단계",
            "last_message": "요즘 많이 좋아졌어요. 배운 것들을 계속 실천하고 있습니다",
            "user_age": 35,
            "cbt_stage": 5
        }
    ]

    results = []

    for scenario in test_scenarios:
        # Determine age group
        age = scenario["user_age"]
        age_group = AgeGroup.ADOLESCENT if 13 <= age <= 18 else AgeGroup.ADULT

        # Get CBT stage
        cbt_stage = CBTStage(scenario["cbt_stage"])

        # Build context
        conversation_context = {
            "messages": [{"content": scenario["last_message"], "role": "user"}],
            "user_age_group": age_group.value
        }

        # Select prompt
        result = await prompt_service.select_prompt(
            conversation_context=conversation_context,
            age_group=age_group,
            cbt_stage=cbt_stage,
            last_message=scenario["last_message"]
        )

        results.append({
            "scenario": scenario["name"],
            "input": {
                "message": scenario["last_message"],
                "age": scenario["user_age"],
                "stage": scenario["cbt_stage"]
            },
            "output": {
                "prompt_key": result["prompt_key"],
                "reasoning": result["reasoning"],
                "factors": result["factors"],
                "prompt_preview": result["selected_prompt"][:200] + "..."
            }
        })

    return {
        "total_scenarios": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/prompts/emotions/keywords")
async def get_emotion_keywords(
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service)
):
    """
    Get emotion detection keyword mappings

    감정 탐지 키워드 매핑 조회

    **Returns:**
    Dictionary of emotions and their associated keywords with intensity levels
    """
    return {
        "emotion_keywords": prompt_service.emotion_detector.EMOTION_KEYWORDS,
        "available_emotions": [e.value for e in EmotionType],
        "intensity_levels": {
            "high": "7-10 (극도, 매우 높음)",
            "moderate": "4-6 (보통)",
            "low": "1-3 (낮음, 최소)"
        }
    }


@router.post("/prompts/detect-special-situation")
async def detect_special_situation(
    message: str = Field(..., description="User message to analyze"),
    message_count: int = Field(default=5, description="Number of messages in conversation"),
    prompt_service: DynamicPromptService = Depends(get_dynamic_prompt_service)
):
    """
    Detect special counseling situations

    특수 상담 상황 탐지

    **Detects:**
    - First Session (첫 세션): < 3 messages
    - Breakthrough (돌파구): Insight keywords + excitement
    - Resistance (저항): Dismissive language, short responses
    - None (일반): Normal conversation

    **Example:**
    ```json
    {
        "message": "모르겠어요. 별로 도움 안 되는 것 같아요",
        "message_count": 10
    }
    ```

    **Response:**
    ```json
    {
        "special_situation": "resistance",
        "detected": true,
        "confidence": "high",
        "description": "저항적 태도 감지"
    }
    ```
    """
    try:
        # Build conversation context
        conversation_context = {
            "messages": [{"content": message, "role": "user"}] * message_count
        }

        # Detect special situation
        special_situation = prompt_service.special_situation_detector.detect(
            message=message,
            conversation_context=conversation_context
        )

        # Get description
        descriptions = {
            SpecialSituation.FIRST_SESSION: "첫 세션 - 라포 형성 및 신뢰 구축",
            SpecialSituation.RESISTANCE: "저항적 태도 - 비판단적 탐색 필요",
            SpecialSituation.BREAKTHROUGH: "돌파구 순간 - 중요한 통찰 발생",
            SpecialSituation.NONE: "일반 상담 상황"
        }

        return {
            "special_situation": special_situation.value,
            "detected": special_situation != SpecialSituation.NONE,
            "confidence": "high",
            "description": descriptions[special_situation],
            "prompt_key": special_situation.value.upper() if special_situation != SpecialSituation.NONE else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Special situation detection failed: {str(e)}")


@router.get("/prompts/special-situations")
async def get_special_situations():
    """
    Get all special situation types and descriptions

    특수 상황 목록 조회

    **Returns:**
    List of special situations with descriptions and indicators
    """
    situations = [
        {
            "type": "first_session",
            "name_ko": "첫 세션",
            "description": "내담자와의 첫 만남. 라포 형성 및 안전한 관계 구축이 목표",
            "indicators": [
                "메시지 수 < 3",
                "초기 인사 및 소개"
            ],
            "priority": 1,
            "prompt_key": "FIRST_SESSION"
        },
        {
            "type": "breakthrough",
            "name_ko": "돌파구 순간",
            "description": "중요한 통찰과 깨달음이 일어나는 순간. 변화의 전환점",
            "indicators": [
                "통찰 키워드: '이해가 되네', '깨달았어', '알겠네'",
                "강한 감정 표출 (놀람, 기쁨)",
                "연결고리 발견"
            ],
            "priority": 2,
            "prompt_key": "BREAKTHROUGH"
        },
        {
            "type": "resistance",
            "name_ko": "저항적 태도",
            "description": "변화에 대한 저항, 방어적 태도. 비판단적 탐색 필요",
            "indicators": [
                "거부 키워드: '모르겠어', '별로', '그냥'",
                "짧고 무성의한 응답",
                "주제 회피",
                "냉소적 태도"
            ],
            "priority": 3,
            "prompt_key": "RESISTANCE"
        },
        {
            "type": "none",
            "name_ko": "일반 상황",
            "description": "특별한 상황이 감지되지 않음. 정상적인 상담 진행",
            "indicators": [
                "특수 상황 조건 미충족"
            ],
            "priority": 4,
            "prompt_key": None
        }
    ]

    return {
        "special_situations": situations,
        "total_count": len(situations),
        "detection_priority": "First Session > Breakthrough > Resistance > None"
    }


@router.get("/prompts/library-complete")
async def get_complete_prompt_library():
    """
    Get COMPLETE prompt library including all special situations

    완전한 프롬프트 라이브러리 조회 (특수 상황 포함)

    **Returns:**
    All 20+ prompts organized by category
    """
    prompts = {
        "crisis": [
            {
                "key": "CRISIS_INTERVENTION",
                "name_ko": "위기 개입",
                "target": "Level 3-4 자살/자해 위험",
                "priority": "최우선"
            }
        ],
        "teen_prompts": [
            {"key": "TEEN_ASSESSMENT_ANXIETY", "name_ko": "청소년 초기평가-불안", "stage": 1, "emotion": "anxiety"},
            {"key": "TEEN_ASSESSMENT_DEPRESSION", "name_ko": "청소년 초기평가-우울", "stage": 1, "emotion": "depression"},
            {"key": "TEEN_RECONCEPTUALIZATION_ANXIETY", "name_ko": "청소년 재개념화-불안", "stage": 2, "emotion": "anxiety"},
            {"key": "TEEN_RECONCEPTUALIZATION_DEPRESSION", "name_ko": "청소년 재개념화-우울", "stage": 2, "emotion": "depression"},
            {"key": "TEEN_SKILLS_ANXIETY", "name_ko": "청소년 기술습득-불안", "stage": 3, "emotion": "anxiety"},
            {"key": "TEEN_APPLICATION_ANGER", "name_ko": "청소년 기술적용-분노", "stage": 4, "emotion": "anger"},
            {"key": "TEEN_MAINTENANCE_NEUTRAL", "name_ko": "청소년 유지관리-안정", "stage": 5, "emotion": "neutral"}
        ],
        "adult_prompts": [
            {"key": "ADULT_ASSESSMENT_ANXIETY", "name_ko": "성인 초기평가-불안", "stage": 1, "emotion": "anxiety"},
            {"key": "ADULT_ASSESSMENT_DEPRESSION", "name_ko": "성인 초기평가-우울", "stage": 1, "emotion": "depression"},
            {"key": "ADULT_RECONCEPTUALIZATION_ANXIETY", "name_ko": "성인 재개념화-불안", "stage": 2, "emotion": "anxiety"},
            {"key": "ADULT_RECONCEPTUALIZATION_DEPRESSION", "name_ko": "성인 재개념화-우울", "stage": 2, "emotion": "depression"},
            {"key": "ADULT_SKILLS_DEPRESSION", "name_ko": "성인 기술습득-우울", "stage": 3, "emotion": "depression"},
            {"key": "ADULT_APPLICATION_ANXIETY", "name_ko": "성인 기술적용-불안", "stage": 4, "emotion": "anxiety"},
            {"key": "ADULT_APPLICATION_DEPRESSION", "name_ko": "성인 기술적용-우울", "stage": 4, "emotion": "depression"},
            {"key": "ADULT_MAINTENANCE_NEUTRAL", "name_ko": "성인 유지관리-안정", "stage": 5, "emotion": "neutral"}
        ],
        "special_situations": [
            {"key": "FIRST_SESSION", "name_ko": "첫 세션", "description": "라포 형성 및 신뢰 구축"},
            {"key": "RESISTANCE", "name_ko": "저항적 태도", "description": "비판단적 탐색 및 협력 강화"},
            {"key": "BREAKTHROUGH", "name_ko": "돌파구 순간", "description": "통찰 명확화 및 변화 강화"}
        ],
        "fallback": [
            {"key": "DEFAULT_GENERAL", "name_ko": "일반 상담", "description": "기본 심리상담 프롬프트"}
        ]
    }

    total = (len(prompts["crisis"]) +
             len(prompts["teen_prompts"]) +
             len(prompts["adult_prompts"]) +
             len(prompts["special_situations"]) +
             len(prompts["fallback"]))

    return {
        "prompts": prompts,
        "total_count": total,
        "categories": {
            "crisis": 1,
            "teen": len(prompts["teen_prompts"]),
            "adult": len(prompts["adult_prompts"]),
            "special": len(prompts["special_situations"]),
            "fallback": 1
        }
    }
