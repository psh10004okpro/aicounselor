"""
Real-time Analysis API Endpoints
실시간 분석 API

Provides endpoints for GPT-4 powered message analysis and dynamic prompt selection.

Author: AI Counselor System
Date: 2025-11-05
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

from app.services.realtime_analyzer import (
    RealtimeMessageAnalyzer,
    EnhancedPromptSelector
)
from app.services.openai_service import OpenAIService
from app.services.alert_system import CrisisAlertSystem, AlertResponse


router = APIRouter(prefix="/api", tags=["realtime-analysis"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MessageAnalysisRequest(BaseModel):
    """Request for message analysis"""
    message: str = Field(..., description="User message to analyze")
    conversation_context: Optional[List[Dict]] = Field(None, description="Previous messages")
    user_profile: Optional[Dict] = Field(None, description="User profile (age, session_count, etc.)")
    generate_alert: bool = Field(False, description="Whether to generate alert if crisis detected")
    user_id: Optional[str] = Field(None, description="User ID for alert generation")


class MessageAnalysisResponse(BaseModel):
    """Response for message analysis"""
    emotions: Dict
    crisis_level: int
    crisis_indicators: List[str]
    session_stage_suggestion: str
    recommended_approach: str
    confidence: float
    analysis_timestamp: str
    alert: Optional[Dict] = None  # Alert info if generated


class PromptSelectionRequest(BaseModel):
    """Request for dynamic prompt selection"""
    user_message: str = Field(..., description="Current user message")
    user_profile: Dict = Field(..., description="User profile with age, session_count")
    conversation_history: List[Dict] = Field(default=[], description="Previous conversation")
    memory_context: str = Field(default="", description="Retrieved memory context")


class PromptSelectionResponse(BaseModel):
    """Response for prompt selection"""
    selected_prompt: str
    prompt_key: str
    analysis: Dict
    reasoning: str
    selection_timestamp: str


class BatchAnalysisRequest(BaseModel):
    """Request for batch conversation analysis"""
    messages: List[str] = Field(..., description="List of messages to analyze")
    user_profile: Optional[Dict] = Field(None, description="User profile")


# ============================================================================
# Helper Functions
# ============================================================================

def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance"""
    return OpenAIService()


def get_message_analyzer(
    openai_service: OpenAIService = Depends(get_openai_service)
) -> RealtimeMessageAnalyzer:
    """Get message analyzer instance"""
    return RealtimeMessageAnalyzer(openai_client=openai_service.client)


def get_alert_system() -> CrisisAlertSystem:
    """Get alert system instance"""
    return CrisisAlertSystem()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/analyze/message", response_model=MessageAnalysisResponse)
async def analyze_message(
    request: MessageAnalysisRequest,
    analyzer: RealtimeMessageAnalyzer = Depends(get_message_analyzer),
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Analyze message using GPT-4 for comprehensive insights

    GPT-4를 사용한 메시지 종합 분석

    **Analyzes:**
    - Primary and secondary emotions
    - Emotion intensity (0.0-1.0)
    - Crisis level (0-4 C-SSRS scale)
    - Crisis indicators/keywords
    - Recommended CBT stage
    - Suggested therapeutic approach
    - Analysis confidence level
    - **Optional:** Generate crisis alert if requested

    **Example Request (with alert generation):**
    ```json
    {
        "message": "죽고 싶어요",
        "user_profile": {
            "age": 17
        },
        "generate_alert": true,
        "user_id": "user123"
    }
    ```

    **Example Response:**
    ```json
    {
        "emotions": {
            "primary": "depression",
            "secondary": ["hopelessness"],
            "intensity": 0.95
        },
        "crisis_level": 4,
        "crisis_indicators": ["죽고 싶"],
        "session_stage_suggestion": "assessment",
        "recommended_approach": "즉각적 위기 개입 필요",
        "confidence": 0.9,
        "alert": {
            "alert_type": "emergency",
            "priority": "critical",
            "message": "⚠️ **긴급 상황 감지**...",
            "emergency_contacts": [...],
            "admin_notified": true
        }
    }
    ```
    """
    try:
        # Perform GPT-4 analysis
        analysis = await analyzer.analyze_message(
            message=request.message,
            conversation_context=request.conversation_context,
            user_profile=request.user_profile
        )

        # Add timestamp
        analysis["analysis_timestamp"] = datetime.now().isoformat()

        # Generate alert if requested and crisis detected
        alert_data = None
        if request.generate_alert and analysis["crisis_level"] >= 2:
            if not request.user_id:
                raise HTTPException(
                    status_code=400,
                    detail="user_id required when generate_alert is true"
                )

            alert_response = await alert_system.check_and_alert(
                crisis_level=analysis["crisis_level"],
                user_id=request.user_id,
                message=request.message,
                crisis_indicators=analysis["crisis_indicators"],
                user_age=request.user_profile.get("age") if request.user_profile else None
            )

            # Convert to dict for response
            alert_data = alert_response.model_dump()

        analysis["alert"] = alert_data

        return MessageAnalysisResponse(**analysis)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Message analysis failed: {str(e)}"
        )


@router.post("/analyze/select-prompt", response_model=PromptSelectionResponse)
async def select_dynamic_prompt_endpoint(
    request: PromptSelectionRequest,
    analyzer: RealtimeMessageAnalyzer = Depends(get_message_analyzer)
):
    """
    Select optimal prompt based on GPT-4 analysis

    GPT-4 분석 기반 최적 프롬프트 선택

    **Selection Priority:**
    1. Crisis level 3-4 → Crisis intervention prompt
    2. GPT-4 suggested stage + age + emotion → Specific prompt
    3. Fallback → Default prompt

    **Example Request:**
    ```json
    {
        "user_message": "학교 가기가 너무 불안해요",
        "user_profile": {
            "age": 16,
            "session_count": 1
        },
        "conversation_history": [
            {"role": "user", "content": "안녕하세요"}
        ],
        "memory_context": "이전에 시험 불안에 대해 이야기함"
    }
    ```

    **Example Response:**
    ```json
    {
        "prompt_key": "teen_assessment_anxiety",
        "analysis": {
            "emotions": {"primary": "anxiety", "intensity": 0.8},
            "crisis_level": 1,
            "session_stage_suggestion": "assessment"
        },
        "reasoning": "청소년 + 초기 평가 + 불안 감정 (강도 높음) | GPT-4 분석 신뢰도: 높음"
    }
    ```
    """
    try:
        # For demonstration, using a minimal prompt library
        # In production, this would use the full PromptLibrary
        prompt_library = {
            "crisis_level_3": "위기 개입 프롬프트...",
            "teen_assessment_anxiety": "청소년 불안 초기 평가...",
            "teen_assessment_depression": "청소년 우울 초기 평가...",
            "adult_assessment_anxiety": "성인 불안 초기 평가...",
            "adult_assessment_depression": "성인 우울 초기 평가...",
            "default": "일반 상담 프롬프트..."
        }

        # Create enhanced selector
        selector = EnhancedPromptSelector(
            message_analyzer=analyzer,
            prompt_library=prompt_library
        )

        # Select prompt
        result = await selector.select_dynamic_prompt(
            user_message=request.user_message,
            user_profile=request.user_profile,
            conversation_history=request.conversation_history,
            memory_context=request.memory_context
        )

        # Add timestamp
        result["selection_timestamp"] = datetime.now().isoformat()

        return PromptSelectionResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prompt selection failed: {str(e)}"
        )


@router.post("/analyze/batch")
async def batch_analyze_conversation(
    request: BatchAnalysisRequest,
    analyzer: RealtimeMessageAnalyzer = Depends(get_message_analyzer)
):
    """
    Analyze multiple messages in batch

    여러 메시지 일괄 분석

    **Use Case:**
    - Analyzing entire conversation history
    - Tracking emotional progression over time
    - Identifying crisis patterns

    **Example Request:**
    ```json
    {
        "messages": [
            "안녕하세요",
            "요즘 너무 불안해요",
            "밤에 잠도 못 자고 계속 걱정돼요"
        ],
        "user_profile": {
            "age": 25,
            "session_count": 1
        }
    }
    ```

    **Example Response:**
    ```json
    {
        "analyses": [
            {
                "message_index": 0,
                "message": "안녕하세요",
                "emotions": {"primary": "neutral", "intensity": 0.1},
                "crisis_level": 0
            },
            {
                "message_index": 1,
                "message": "요즘 너무 불안해요",
                "emotions": {"primary": "anxiety", "intensity": 0.7},
                "crisis_level": 1
            },
            {
                "message_index": 2,
                "message": "밤에 잠도 못 자고 계속 걱정돼요",
                "emotions": {"primary": "anxiety", "intensity": 0.8},
                "crisis_level": 2
            }
        ],
        "summary": {
            "total_messages": 3,
            "highest_crisis_level": 2,
            "dominant_emotion": "anxiety",
            "average_intensity": 0.53
        }
    }
    ```
    """
    try:
        # Analyze each message
        analyses = await analyzer.batch_analyze_conversation(
            messages=request.messages,
            user_profile=request.user_profile
        )

        # Build response with indices
        detailed_analyses = []
        for i, (message, analysis) in enumerate(zip(request.messages, analyses)):
            detailed_analyses.append({
                "message_index": i,
                "message": message,
                **analysis
            })

        # Generate summary
        crisis_levels = [a["crisis_level"] for a in analyses]
        intensities = [a["emotions"]["intensity"] for a in analyses]
        emotions = [a["emotions"]["primary"] for a in analyses]

        # Find dominant emotion
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)

        summary = {
            "total_messages": len(request.messages),
            "highest_crisis_level": max(crisis_levels) if crisis_levels else 0,
            "dominant_emotion": dominant_emotion,
            "average_intensity": sum(intensities) / len(intensities) if intensities else 0.0,
            "emotion_distribution": emotion_counts
        }

        return {
            "analyses": detailed_analyses,
            "summary": summary,
            "batch_timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch analysis failed: {str(e)}"
        )


@router.post("/analyze/quick")
async def quick_analysis(
    message: str = Field(..., description="Message to analyze"),
    user_id: Optional[str] = Field(None, description="User ID for alert generation"),
    analyzer: RealtimeMessageAnalyzer = Depends(get_message_analyzer),
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Quick message analysis (simplified) with automatic alert generation

    빠른 메시지 분석 (간소화 버전) - 자동 경고 생성

    **Use Case:**
    - Fast emotion check
    - Crisis screening
    - Real-time chat monitoring
    - **Automatic alert generation for crisis levels 3-4**

    **Example:**
    ```
    POST /api/analyze/quick
    {
        "message": "죽고 싶어요",
        "user_id": "user123"
    }
    ```

    **Response:**
    ```json
    {
        "crisis_level": 4,
        "primary_emotion": "depression",
        "intensity": 0.95,
        "immediate_action_required": true,
        "recommendation": "즉시 위기 개입 필요 - 119 또는 1393 연결",
        "emergency_contact": "1393",
        "alert_generated": true,
        "alert_summary": "긴급 상황 - 관리자 알림 전송됨"
    }
    ```
    """
    try:
        # Perform analysis
        analysis = await analyzer.analyze_message(
            message=message,
            conversation_context=None,
            user_profile=None
        )

        # Simplified response
        crisis_level = analysis["crisis_level"]
        primary_emotion = analysis["emotions"]["primary"]
        intensity = analysis["emotions"]["intensity"]

        # Determine immediate action
        immediate_action_required = crisis_level >= 3
        recommendation = ""
        emergency_contact = None

        if crisis_level >= 4:
            recommendation = "즉시 위기 개입 필요 - 119 또는 1393 연결"
            emergency_contact = "1393"
        elif crisis_level == 3:
            recommendation = "높은 위험 - 전문가 개입 및 모니터링 필요"
            emergency_contact = "1393"
        elif crisis_level == 2:
            recommendation = "중간 위험 - 주의 깊은 관찰 및 지원"
            emergency_contact = "1393"
        elif crisis_level == 1:
            recommendation = "낮은 위험 - 일반 상담 진행"
        else:
            recommendation = "안전 - 정상적인 대화 진행"

        # Generate alert for high-risk situations
        alert_generated = False
        alert_summary = None

        if crisis_level >= 3 and user_id:
            alert_response = await alert_system.check_and_alert(
                crisis_level=crisis_level,
                user_id=user_id,
                message=message,
                crisis_indicators=analysis["crisis_indicators"]
            )
            alert_generated = True
            alert_summary = f"{alert_response.alert_type.value} - "
            if alert_response.admin_notified:
                alert_summary += "관리자 알림 전송됨"
            else:
                alert_summary += "모니터링 필요"

        return {
            "crisis_level": crisis_level,
            "primary_emotion": primary_emotion,
            "intensity": intensity,
            "immediate_action_required": immediate_action_required,
            "recommendation": recommendation,
            "emergency_contact": emergency_contact,
            "alert_generated": alert_generated,
            "alert_summary": alert_summary,
            "full_analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quick analysis failed: {str(e)}"
        )


@router.get("/analyze/capabilities")
async def get_analysis_capabilities():
    """
    Get analysis system capabilities and configuration

    분석 시스템 기능 및 설정 조회

    **Returns:**
    System capabilities, supported features, and configuration
    """
    return {
        "system": "GPT-4 Powered Real-time Analysis",
        "version": "1.0.0",
        "capabilities": {
            "emotion_detection": {
                "supported_emotions": [
                    "anxiety", "depression", "anger", "fear",
                    "sadness", "joy", "shame", "guilt", "neutral"
                ],
                "intensity_range": "0.0 - 1.0",
                "secondary_emotions": True
            },
            "crisis_detection": {
                "scale": "C-SSRS (0-4)",
                "levels": {
                    "0": "안전 (Safe)",
                    "1": "낮음 (Low)",
                    "2": "중간 (Moderate)",
                    "3": "높음 (High)",
                    "4": "긴급 (Imminent)"
                },
                "indicator_extraction": True
            },
            "cbt_stage_suggestion": {
                "supported_stages": [
                    "assessment", "reconceptualization", "skills",
                    "application", "maintenance", "termination"
                ],
                "confidence_scoring": True
            },
            "therapeutic_recommendations": True,
            "batch_analysis": True,
            "context_awareness": True
        },
        "performance": {
            "analysis_time": "~2-4 seconds (GPT-4 latency)",
            "batch_limit": 20,
            "concurrent_requests": "Unlimited"
        },
        "integration": {
            "dynamic_prompt_selection": True,
            "crisis_intervention_trigger": True,
            "memory_context_support": True
        }
    }
