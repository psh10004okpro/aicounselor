"""
CBT Stage Management API Endpoints

Provides endpoints for managing and monitoring CBT therapy stages:
- Get current stage information
- Transition to next stage
- Get stage progress
- Get stage assessment history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

from app.core.database import get_db
from app.services.cbt_stage_service import CBTStageService, CBTStage
from app.services.openai_service import OpenAIService
from app.services.cache_service import CacheService
from app.core.redis import RedisManager
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cbt", tags=["CBT Stages"])


# Dependency to get CBT stage service
async def get_cbt_service(db: AsyncSession = Depends(get_db)) -> CBTStageService:
    """Get CBT stage service instance"""
    # Initialize OpenAI client for assessments
    redis_manager = RedisManager(settings.REDIS_URL)
    await redis_manager.connect()

    cache_service = CacheService(redis_manager)
    openai_service = OpenAIService(cache_service)

    return CBTStageService(db=db, openai_client=openai_service.client)


@router.get("/stages/{conversation_id}", response_model=Dict[str, Any])
async def get_current_stage(
    conversation_id: str,
    cbt_service: CBTStageService = Depends(get_cbt_service)
):
    """
    Get current CBT stage for a conversation

    Returns stage information including:
    - Current stage number and name
    - Stage progress percentage
    - Goals achieved and pending
    - Readiness for next stage
    """
    try:
        stage = await cbt_service.get_current_stage(conversation_id)
        progress = await cbt_service.get_stage_progress(conversation_id)

        return {
            "success": True,
            "conversation_id": conversation_id,
            "current_stage": {
                "stage_number": stage.num,
                "stage_name": stage.stage_name,
                "korean_name": stage.korean_name,
            },
            "progress": progress
        }

    except Exception as e:
        logger.error(f"Error getting current stage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current stage: {str(e)}"
        )


@router.post("/stages/{conversation_id}/initialize")
async def initialize_conversation_stage(
    conversation_id: str,
    cbt_service: CBTStageService = Depends(get_cbt_service)
):
    """
    Initialize CBT stage tracking for a new conversation

    Automatically creates stage record starting at Assessment (Stage 1)
    """
    try:
        success = await cbt_service.initialize_stage(conversation_id)

        if success:
            return {
                "success": True,
                "message": "CBT stage initialized successfully",
                "conversation_id": conversation_id,
                "initial_stage": {
                    "stage_number": 1,
                    "stage_name": "assessment",
                    "korean_name": "초기 평가"
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to initialize stage"
            )

    except Exception as e:
        logger.error(f"Error initializing stage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize stage: {str(e)}"
        )


@router.post("/stages/{conversation_id}/assess")
async def assess_stage_progress(
    conversation_id: str,
    recent_messages: List[Dict[str, str]],
    cbt_service: CBTStageService = Depends(get_cbt_service)
):
    """
    Manually trigger stage progress assessment

    Analyzes recent messages to evaluate:
    - Progress toward stage goals
    - Readiness for next stage
    - Recommendation (continue/advance/review)

    Body: { "recent_messages": [{"role": "user", "content": "..."}, ...] }
    """
    try:
        assessment = await cbt_service.assess_stage_progress_auto(
            conversation_id=conversation_id,
            recent_messages=recent_messages
        )

        if assessment:
            return {
                "success": True,
                "conversation_id": conversation_id,
                "assessment": assessment
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Assessment failed"
            )

    except Exception as e:
        logger.error(f"Error assessing stage progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess progress: {str(e)}"
        )


@router.post("/stages/{conversation_id}/advance", response_model=Dict[str, Any])
async def advance_to_next_stage(
    conversation_id: str,
    force: bool = False,
    cbt_service: CBTStageService = Depends(get_cbt_service)
):
    """
    Advance conversation to next CBT stage

    Query params:
    - force: Force transition even if not ready (default: False)

    Checks readiness before advancing (unless forced):
    - Requires 70%+ readiness score
    - Recommendation should be 'advance'

    Returns new stage information if successful
    """
    try:
        result = await cbt_service.transition_to_next_stage(
            conversation_id=conversation_id,
            force=force
        )

        if result.get('success'):
            return {
                "success": True,
                "message": result.get('message'),
                "conversation_id": conversation_id,
                "previous_stage": result.get('previous_stage'),
                "current_stage": {
                    "stage_number": result.get('current_stage'),
                    "stage_name": result.get('stage_name'),
                    "korean_name": result.get('korean_name')
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('message', 'Cannot advance to next stage')
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing stage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to advance stage: {str(e)}"
        )


@router.get("/stages/{conversation_id}/history")
async def get_stage_history(
    conversation_id: str,
    cbt_service: CBTStageService = Depends(get_cbt_service)
):
    """
    Get complete stage transition history for a conversation

    Returns chronological history of:
    - Stage transitions
    - Time spent in each stage
    - Goals achieved per stage
    """
    try:
        progress = await cbt_service.get_stage_progress(conversation_id)

        # Get stage history from progress data
        stage_history = progress.get('stage_history', [])

        return {
            "success": True,
            "conversation_id": conversation_id,
            "stage_history": stage_history,
            "current_stage": {
                "stage_number": progress.get('current_stage'),
                "stage_name": progress.get('stage_name')
            }
        }

    except Exception as e:
        logger.error(f"Error getting stage history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stage history: {str(e)}"
        )


@router.get("/stages/{conversation_id}/assessments")
async def get_assessment_history(
    conversation_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get assessment history for a conversation

    Query params:
    - limit: Maximum number of assessments to return (default: 10)

    Returns chronological list of automatic assessments
    """
    try:
        result = await db.execute(
            """
            SELECT
                assessment_id,
                stage,
                stage_name,
                assessment_type,
                assessment_result,
                messages_analyzed,
                assessed_at
            FROM stage_assessments
            WHERE conversation_id = $1
            ORDER BY assessed_at DESC
            LIMIT $2
            """,
            conversation_id,
            limit
        )
        assessments = result.fetchall()

        return {
            "success": True,
            "conversation_id": conversation_id,
            "assessments": [
                {
                    "assessment_id": str(a['assessment_id']),
                    "stage": a['stage'],
                    "stage_name": a['stage_name'],
                    "assessment_type": a['assessment_type'],
                    "assessment_result": a['assessment_result'],
                    "messages_analyzed": a['messages_analyzed'],
                    "assessed_at": a['assessed_at'].isoformat()
                }
                for a in assessments
            ],
            "total": len(assessments)
        }

    except Exception as e:
        logger.error(f"Error getting assessment history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment history: {str(e)}"
        )


@router.get("/info/stages")
async def get_all_stages_info():
    """
    Get information about all 6 CBT stages

    Returns comprehensive information:
    - Stage number, name, Korean name
    - Stage description
    - Key goals
    - Typical duration
    """
    stages_info = []

    for stage in CBTStage:
        stages_info.append({
            "stage_number": stage.num,
            "stage_name": stage.stage_name,
            "korean_name": stage.korean_name,
            "goals": CBTStageService.STAGE_GOALS.get(stage, []),
            "description": get_stage_description(stage)
        })

    return {
        "success": True,
        "total_stages": 6,
        "stages": stages_info
    }


def get_stage_description(stage: CBTStage) -> str:
    """Get brief description of each stage"""
    descriptions = {
        CBTStage.ASSESSMENT: "라포 형성, 문제 파악, 신뢰 구축을 목표로 하는 초기 평가 단계",
        CBTStage.RECONCEPTUALIZATION: "생각-감정-행동 연결고리 이해, ABC 모델 학습 단계",
        CBTStage.SKILLS_ACQUISITION: "인지 재구조화, 문제 해결 등 CBT 기법을 배우는 단계",
        CBTStage.SKILLS_APPLICATION: "배운 기법을 실생활에 적용하고 숙제를 수행하는 단계",
        CBTStage.GENERALIZATION: "재발 방지 계획 수립, 장기적 적용을 준비하는 단계",
        CBTStage.TERMINATION: "성과 축하, 향후 계획 수립, 긍정적 종결 단계"
    }
    return descriptions.get(stage, "")


@router.get("/info/stages/{stage_number}")
async def get_stage_info(stage_number: int):
    """
    Get detailed information about a specific stage

    Path params:
    - stage_number: Stage number (1-6)
    """
    if stage_number < 1 or stage_number > 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stage number must be between 1 and 6"
        )

    stage = CBTStageService.get_stage_by_number(stage_number)

    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not found"
        )

    return {
        "success": True,
        "stage": {
            "stage_number": stage.num,
            "stage_name": stage.stage_name,
            "korean_name": stage.korean_name,
            "goals": CBTStageService.STAGE_GOALS.get(stage, []),
            "description": get_stage_description(stage),
            "system_prompt_preview": CBTStageService.STAGE_PROMPTS.get(stage, "")[:500] + "..."
        }
    }
