"""
Crisis Assessment API Endpoints

Provides ASQ screening and C-SSRS based crisis assessment
"""

from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.crisis_detector_enhanced import (
    enhanced_crisis_detection_system,
    ASQScreening,
    CrisisFramework,
    CSSRSLevel,
    RiskLevel
)


router = APIRouter(prefix="/crisis", tags=["crisis-assessment"])


# Request/Response Models

class ASQResponse(BaseModel):
    """ASQ questionnaire response"""
    asq1: bool = Field(description="Past 2 weeks: thoughts of death or self-harm")
    asq2: bool = Field(description="Past 3 months: plan to harm self")
    asq3: bool = Field(description="Past year: attempt to harm self")
    asq4: bool = Field(description="Lifetime: past suicide attempt")


class ASQAssessmentRequest(BaseModel):
    """Request for ASQ assessment"""
    conversation_id: Optional[str] = None
    asq_responses: ASQResponse
    current_message: Optional[str] = None


class CrisisAssessmentRequest(BaseModel):
    """Request for crisis assessment with optional ASQ"""
    message: str
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[Dict]] = None
    asq_responses: Optional[ASQResponse] = None


class CSSRSLevelInfo(BaseModel):
    """C-SSRS level information"""
    level: int
    name: str
    name_en: str
    indicators: List[str]
    assessment_criteria: List[str]
    action: str
    action_detail: str
    resources: List[str]
    monitoring_frequency: str


class CrisisAssessmentResponse(BaseModel):
    """Crisis assessment response"""
    success: bool
    risk_level: str
    cssrs_level: int
    cssrs_level_name: str
    detected_keywords: List[str]
    keyword_categories: Dict[str, List[str]]
    reasoning: str
    immediate_action_needed: bool
    suggested_resources: List[str]
    action_required: str
    action_detail: str
    confidence: float
    detection_method: str
    response_message: str
    asq_result: Optional[Dict] = None


# Endpoints

@router.get("/asq/questions")
async def get_asq_questions():
    """
    Get ASQ (Ask Suicide-Screening Questions) 4-item questionnaire

    Returns all 4 ASQ questions in Korean and English
    """
    questions = ASQScreening.get_questions()

    return {
        "success": True,
        "total_questions": len(questions),
        "questions": questions,
        "instructions": {
            "ko": "다음 질문들에 '예' 또는 '아니오'로 답해주세요. 하나라도 '예'라면 전문가 평가가 권장됩니다.",
            "en": "Please answer 'Yes' or 'No' to each question. If any answer is 'Yes', professional evaluation is recommended."
        },
        "scoring": {
            "info": "Any positive response indicates need for professional assessment",
            "action_if_positive": "Immediate professional evaluation required"
        }
    }


@router.post("/asq/assess", response_model=CrisisAssessmentResponse)
async def assess_asq(
    request: ASQAssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Assess ASQ responses

    Evaluates ASQ questionnaire responses and provides risk assessment
    based on C-SSRS framework
    """
    # Convert Pydantic model to dict
    asq_dict = {
        "asq1": request.asq_responses.asq1,
        "asq2": request.asq_responses.asq2,
        "asq3": request.asq_responses.asq3,
        "asq4": request.asq_responses.asq4
    }

    # Evaluate ASQ
    asq_result = ASQScreening.evaluate_responses(asq_dict)

    # Get level info
    cssrs_level = asq_result["cssrs_level"]
    level_info = CrisisFramework.get_level_info(cssrs_level)

    # Create full assessment
    assessment = {
        "risk_level": asq_result["risk_level"].value,
        "cssrs_level": cssrs_level.value,
        "cssrs_level_name": level_info["name"],
        "detected_keywords": [],
        "keyword_categories": {},
        "reasoning": f"ASQ 선별검사 결과: {asq_result['positive_count']}개 항목 양성",
        "immediate_action_needed": asq_result["asq_positive"],
        "suggested_resources": level_info["resources"],
        "action_required": level_info["action"],
        "action_detail": level_info["action_detail"],
        "confidence": 0.95,
        "detection_method": "asq_screening",
        "asq_result": asq_result
    }

    # Get appropriate response message
    response_message = enhanced_crisis_detection_system.get_crisis_response_message(
        assessment
    )

    # Log assessment if conversation_id provided
    if request.conversation_id:
        await enhanced_crisis_detection_system.emergency_protocol(
            assessment=assessment,
            user_id="asq_assessment",  # TODO: Get actual user_id
            conversation_id=request.conversation_id
        )

    return CrisisAssessmentResponse(
        success=True,
        response_message=response_message,
        **assessment
    )


@router.post("/assess", response_model=CrisisAssessmentResponse)
async def comprehensive_crisis_assessment(
    request: CrisisAssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive crisis assessment

    Performs full crisis assessment including:
    - ASQ screening (if provided)
    - Keyword detection (immediate, high, moderate risk)
    - GPT-4 contextual analysis with C-SSRS framework
    - Risk factor and protective factor identification
    """
    # Convert ASQ responses if provided
    asq_dict = None
    if request.asq_responses:
        asq_dict = {
            "asq1": request.asq_responses.asq1,
            "asq2": request.asq_responses.asq2,
            "asq3": request.asq_responses.asq3,
            "asq4": request.asq_responses.asq4
        }

    # Perform comprehensive assessment
    assessment = await enhanced_crisis_detection_system.detect(
        message=request.message,
        conversation_history=request.conversation_history,
        asq_responses=asq_dict
    )

    # Get response message
    response_message = enhanced_crisis_detection_system.get_crisis_response_message(
        assessment
    )

    # Log and execute emergency protocol if needed
    if assessment["immediate_action_needed"] and request.conversation_id:
        await enhanced_crisis_detection_system.emergency_protocol(
            assessment=assessment,
            user_id="comprehensive_assessment",  # TODO: Get actual user_id
            conversation_id=request.conversation_id
        )

    return CrisisAssessmentResponse(
        success=True,
        risk_level=assessment["risk_level"].value,
        cssrs_level=assessment["cssrs_level"].value,
        cssrs_level_name=assessment["cssrs_level_name"],
        detected_keywords=assessment["detected_keywords"],
        keyword_categories=assessment["keyword_categories"],
        reasoning=assessment["reasoning"],
        immediate_action_needed=assessment["immediate_action_needed"],
        suggested_resources=assessment["suggested_resources"],
        action_required=assessment["action_required"],
        action_detail=assessment["action_detail"],
        confidence=assessment["confidence"],
        detection_method=assessment["detection_method"],
        response_message=response_message,
        asq_result=assessment.get("asq_result")
    )


@router.get("/cssrs/levels")
async def get_cssrs_levels():
    """
    Get all C-SSRS levels information

    Returns detailed information about all 5 C-SSRS levels including
    indicators, assessment criteria, and recommended actions
    """
    levels_info = []

    for cssrs_level in CSSRSLevel:
        level_info = CrisisFramework.get_level_info(cssrs_level)
        levels_info.append({
            "level": cssrs_level.value,
            "name": level_info["name"],
            "name_en": level_info["name_en"],
            "indicators": level_info["indicators"],
            "assessment_criteria": level_info["assessment_criteria"],
            "action": level_info["action"],
            "action_detail": level_info["action_detail"],
            "resources": level_info["resources"],
            "monitoring_frequency": level_info["monitoring_frequency"]
        })

    return {
        "success": True,
        "framework": "Columbia Suicide Severity Rating Scale (C-SSRS)",
        "total_levels": len(levels_info),
        "levels": levels_info,
        "description": {
            "ko": "C-SSRS는 자살 위험도를 5단계로 평가하는 표준화된 도구입니다.",
            "en": "C-SSRS is a standardized tool for assessing suicide risk across 5 levels."
        }
    }


@router.get("/cssrs/levels/{level_number}")
async def get_cssrs_level_info(level_number: int):
    """
    Get specific C-SSRS level information

    Returns detailed information about a specific C-SSRS level
    """
    if level_number < 0 or level_number > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Level number must be between 0 (Safe) and 4 (Imminent)"
        )

    cssrs_level = CSSRSLevel(level_number)
    level_info = CrisisFramework.get_level_info(cssrs_level)

    return {
        "success": True,
        "level": {
            "level": cssrs_level.value,
            "name": level_info["name"],
            "name_en": level_info["name_en"],
            "indicators": level_info["indicators"],
            "assessment_criteria": level_info["assessment_criteria"],
            "action": level_info["action"],
            "action_detail": level_info["action_detail"],
            "resources": level_info["resources"],
            "monitoring_frequency": level_info["monitoring_frequency"]
        }
    }


@router.get("/resources")
async def get_crisis_resources():
    """
    Get crisis intervention resources

    Returns comprehensive list of crisis hotlines and resources
    """
    return {
        "success": True,
        "resources": {
            "emergency": {
                "name": "응급",
                "number": "119",
                "description": "생명이 위험한 즉각적 응급 상황",
                "availability": "24시간"
            },
            "suicide_prevention": {
                "name": "자살예방상담전화",
                "number": "1393",
                "description": "자살 위기 전문 상담",
                "availability": "24시간",
                "free": True
            },
            "lifeline": {
                "name": "생명의 전화",
                "number": "1588-9191",
                "description": "정신건강 위기 상담",
                "availability": "24시간"
            },
            "mental_health_crisis": {
                "name": "정신건강위기상담전화",
                "number": "1577-0199",
                "description": "정신건강 위기 전문 상담",
                "availability": "24시간"
            },
            "police": {
                "name": "경찰",
                "number": "112",
                "description": "긴급 신고",
                "availability": "24시간"
            },
            "online_resources": [
                {
                    "name": "한국생명의전화",
                    "url": "https://www.lifeline.or.kr",
                    "description": "온라인 상담 및 자료"
                },
                {
                    "name": "중앙자살예방센터",
                    "url": "https://www.spckorea.or.kr",
                    "description": "자살 예방 정보 및 자료"
                }
            ]
        },
        "when_to_call": {
            "119": "즉각적 생명 위험 상황",
            "1393": "자살 생각이 들거나 자해 충동이 있을 때",
            "1588-9191": "심각한 우울감이나 정신적 고통",
            "1577-0199": "정신건강 위기 상황"
        }
    }


@router.post("/emergency-protocol/{conversation_id}")
async def trigger_emergency_protocol(
    conversation_id: str,
    assessment_data: Dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger emergency protocol

    Used by counselors or system administrators to manually
    activate emergency intervention procedures
    """
    # TODO: Add authentication/authorization check

    await enhanced_crisis_detection_system.emergency_protocol(
        assessment=assessment_data,
        user_id="manual_trigger",  # TODO: Get actual user_id
        conversation_id=conversation_id
    )

    return {
        "success": True,
        "message": "Emergency protocol activated",
        "conversation_id": conversation_id,
        "timestamp": datetime.utcnow().isoformat()
    }
