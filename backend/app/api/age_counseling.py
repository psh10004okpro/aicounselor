"""
Age-Based Counseling API Endpoints

Provides age-appropriate counseling strategies and recommendations
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.age_based_counseling import (
    age_based_counseling_service,
    AgeGroup,
    AgeBasedCounselingFramework
)


router = APIRouter(prefix="/counseling/age", tags=["age-based-counseling"])


# Request/Response Models

class AgeGroupRequest(BaseModel):
    """Request to determine age group"""
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    birthdate: Optional[str] = Field(None, description="Birthdate (YYYY-MM-DD)")


class AgeGroupResponse(BaseModel):
    """Age group determination response"""
    success: bool
    age_group: str
    age_range: str
    age_range_en: str
    characteristics: list
    communication_style: dict
    session_recommendations: dict


class CounselingStrategyResponse(BaseModel):
    """Complete counseling strategy response"""
    success: bool
    age_group: str
    strategy: dict


class CBTAdaptationRequest(BaseModel):
    """Request for CBT adaptation"""
    age: Optional[int] = None
    birthdate: Optional[str] = None
    cbt_stage: int = Field(ge=1, le=6, description="CBT stage (1-6)")


class CBTAdaptationResponse(BaseModel):
    """CBT adaptation response"""
    success: bool
    age_group: str
    cbt_stage: int
    adaptations: dict
    focus: Optional[str] = None
    techniques: Optional[list] = None


# Endpoints

@router.post("/determine-age-group", response_model=AgeGroupResponse)
async def determine_age_group(request: AgeGroupRequest):
    """
    Determine age group and get basic counseling recommendations

    Accepts either age or birthdate and returns age group classification
    with communication style and session recommendations
    """
    if request.age is None and request.birthdate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either age or birthdate must be provided"
        )

    # Parse birthdate if provided
    birthdate_obj = None
    if request.birthdate:
        try:
            birthdate_obj = date.fromisoformat(request.birthdate)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid birthdate format. Use YYYY-MM-DD"
            )

    # Determine age group
    age_group = age_based_counseling_service.get_age_group_from_user(
        age=request.age,
        birthdate=birthdate_obj
    )

    # Get strategy
    strategy = age_based_counseling_service.get_counseling_strategy(age_group)

    # Get session recommendations
    session_recs = age_based_counseling_service.get_session_recommendations(age_group)

    return AgeGroupResponse(
        success=True,
        age_group=age_group.value,
        age_range=strategy["age_range"],
        age_range_en=strategy["age_range_en"],
        characteristics=strategy["cognitive_characteristics"],
        communication_style=strategy["communication_style"],
        session_recommendations=session_recs
    )


@router.get("/strategies/{age_group}", response_model=CounselingStrategyResponse)
async def get_counseling_strategy(age_group: str):
    """
    Get complete counseling strategy for an age group

    Returns detailed strategy including:
    - Cognitive characteristics
    - Communication style
    - Therapeutic approach
    - CBT adaptations
    - Common issues
    - Crisis considerations
    """
    # Validate age group
    try:
        age_group_enum = AgeGroup(age_group.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid age group. Must be one of: {[g.value for g in AgeGroup]}"
        )

    # Get strategy
    strategy = age_based_counseling_service.get_counseling_strategy(age_group_enum)

    return CounselingStrategyResponse(
        success=True,
        age_group=age_group_enum.value,
        strategy=strategy
    )


@router.get("/strategies")
async def get_all_strategies():
    """
    Get all age group strategies

    Returns counseling strategies for adolescents and adults
    """
    adolescent_strategy = age_based_counseling_service.get_counseling_strategy(
        AgeGroup.ADOLESCENT
    )
    adult_strategy = age_based_counseling_service.get_counseling_strategy(
        AgeGroup.ADULT
    )

    return {
        "success": True,
        "strategies": {
            "adolescent": {
                "age_group": AgeGroup.ADOLESCENT.value,
                "strategy": adolescent_strategy
            },
            "adult": {
                "age_group": AgeGroup.ADULT.value,
                "strategy": adult_strategy
            }
        }
    }


@router.post("/cbt-adaptation", response_model=CBTAdaptationResponse)
async def get_cbt_adaptation(request: CBTAdaptationRequest):
    """
    Get CBT approach adaptation based on age group and stage

    Returns age-appropriate CBT techniques and adaptations for
    the current therapy stage
    """
    if request.age is None and request.birthdate is None:
        # Default to adult if no age info
        age_group = AgeGroup.ADULT
    else:
        # Parse birthdate if provided
        birthdate_obj = None
        if request.birthdate:
            try:
                birthdate_obj = date.fromisoformat(request.birthdate)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid birthdate format. Use YYYY-MM-DD"
                )

        # Determine age group
        age_group = age_based_counseling_service.get_age_group_from_user(
            age=request.age,
            birthdate=birthdate_obj
        )

    # Get CBT adaptations
    adaptations = age_based_counseling_service.adapt_cbt_approach(
        age_group=age_group,
        cbt_stage=request.cbt_stage
    )

    return CBTAdaptationResponse(
        success=True,
        age_group=adaptations["age_group"],
        cbt_stage=adaptations["cbt_stage"],
        adaptations=adaptations["adaptations"],
        focus=adaptations.get("focus"),
        techniques=adaptations.get("techniques")
    )


@router.get("/communication-guidelines/{age_group}")
async def get_communication_guidelines(age_group: str):
    """
    Get communication guidelines for an age group

    Returns detailed communication style, language examples,
    and common issues for the age group
    """
    # Validate age group
    try:
        age_group_enum = AgeGroup(age_group.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid age group. Must be one of: {[g.value for g in AgeGroup]}"
        )

    # Get guidelines
    guidelines = age_based_counseling_service.get_communication_guidelines(
        age_group_enum
    )

    return {
        "success": True,
        **guidelines
    }


@router.get("/session-recommendations/{age_group}")
async def get_session_recommendations(age_group: str):
    """
    Get session configuration recommendations

    Returns recommended session duration, frequency, structure,
    and crisis considerations for the age group
    """
    # Validate age group
    try:
        age_group_enum = AgeGroup(age_group.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid age group. Must be one of: {[g.value for g in AgeGroup]}"
        )

    # Get recommendations
    recommendations = age_based_counseling_service.get_session_recommendations(
        age_group_enum
    )

    return {
        "success": True,
        **recommendations
    }


@router.get("/system-prompt-addition/{age_group}")
async def get_system_prompt_addition(age_group: str):
    """
    Get age-appropriate system prompt additions

    Returns text to add to system prompts for age-appropriate
    counseling approach
    """
    # Validate age group
    try:
        age_group_enum = AgeGroup(age_group.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid age group. Must be one of: {[g.value for g in AgeGroup]}"
        )

    # Get prompt additions
    prompt_addition = AgeBasedCounselingFramework.get_system_prompt_additions(
        age_group_enum
    )

    return {
        "success": True,
        "age_group": age_group_enum.value,
        "prompt_addition": prompt_addition
    }


@router.get("/comparison")
async def get_age_group_comparison():
    """
    Get side-by-side comparison of adolescent and adult strategies

    Returns a comparison table of key differences between
    adolescent and adult counseling approaches
    """
    adolescent = AgeBasedCounselingFramework.ADOLESCENT_STRATEGY
    adult = AgeBasedCounselingFramework.ADULT_STRATEGY

    comparison = {
        "success": True,
        "comparison": {
            "age_range": {
                "adolescent": adolescent["age_range"],
                "adult": adult["age_range"]
            },
            "cognitive_characteristics": {
                "adolescent": adolescent["cognitive_characteristics"],
                "adult": adult["cognitive_characteristics"]
            },
            "communication_tone": {
                "adolescent": adolescent["communication_style"]["tone"],
                "adult": adult["communication_style"]["tone"]
            },
            "session_duration": {
                "adolescent": adolescent["session_characteristics"]["duration"],
                "adult": adult["session_characteristics"]["duration"]
            },
            "structure": {
                "adolescent": adolescent["session_characteristics"]["structure"],
                "adult": adult["session_characteristics"]["structure"]
            },
            "homework_compliance": {
                "adolescent": adolescent["session_characteristics"]["homework_compliance"],
                "adult": adult["session_characteristics"]["homework_compliance"]
            },
            "language_examples": {
                "adolescent": adolescent["language_examples"],
                "adult": adult["language_examples"]
            }
        }
    }

    return comparison
