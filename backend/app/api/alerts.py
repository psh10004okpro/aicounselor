"""
Alert System API Endpoints
경고 시스템 API

Provides endpoints for crisis alert management and emergency contacts.

Author: AI Counselor System
Date: 2025-11-05
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

from app.services.alert_system import (
    CrisisAlertSystem,
    AlertResponse,
    EmergencyContact,
    AlertType,
    AlertPriority
)
from app.constants.crisis_levels import CRISIS_LEVELS_INFO, CRISIS_SCALE_INFO


router = APIRouter(prefix="/api", tags=["alerts"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AlertCheckRequest(BaseModel):
    """Request for checking and generating alert"""
    crisis_level: int = Field(..., ge=0, le=4, description="C-SSRS crisis level (0-4)")
    user_id: str = Field(..., description="User identifier")
    message: Optional[str] = Field(None, description="User message that triggered alert")
    crisis_indicators: Optional[List[str]] = Field(None, description="Detected crisis keywords")
    user_age: Optional[int] = Field(None, description="User age for age-specific recommendations")


class EmergencyContactsRequest(BaseModel):
    """Request for getting emergency contacts"""
    crisis_level: int = Field(..., ge=0, le=4, description="Crisis level")
    user_age: Optional[int] = Field(None, description="User age")


class QuickAlertRequest(BaseModel):
    """Quick alert check with minimal info"""
    crisis_level: int = Field(..., ge=0, le=4, description="Crisis level")
    user_id: str = Field(..., description="User ID")


# ============================================================================
# Helper Functions
# ============================================================================

def get_alert_system() -> CrisisAlertSystem:
    """Get alert system instance"""
    return CrisisAlertSystem()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/alerts/check", response_model=AlertResponse)
async def check_and_generate_alert(
    request: AlertCheckRequest,
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Check crisis level and generate appropriate alert

    위기 수준 확인 및 경고 생성

    **Crisis Levels:**
    - **Level 4 (Emergency)**: Immediate danger
      - Returns emergency hotlines (1393, 1577-0199, 119)
      - Notifies administrators
      - Requires immediate intervention

    - **Level 3 (High Risk)**: Serious concern
      - Returns professional referral contacts
      - Notifies administrators
      - Recommends professional help

    - **Level 2 (Moderate)**: Monitoring needed
      - Returns support contacts
      - Enhanced monitoring recommendations
      - No admin notification

    - **Level 1 (Low)**: Minor concern
      - General self-care recommendations
      - Support contacts for reference

    - **Level 0 (Safe)**: No concern
      - Positive affirmation
      - Wellness maintenance tips

    **Example Request (Level 4 Emergency):**
    ```json
    {
        "crisis_level": 4,
        "user_id": "user123",
        "message": "죽고 싶어요",
        "crisis_indicators": ["죽고 싶", "희망 없"],
        "user_age": 17
    }
    ```

    **Example Response:**
    ```json
    {
        "alert_type": "emergency",
        "priority": "critical",
        "message": "⚠️ **긴급 상황 감지**\\n\\n지금 즉시 전문적인 도움이 필요합니다...",
        "actions_required": ["immediate_intervention"],
        "emergency_contacts": [
            {
                "name": "자살예방상담전화",
                "phone": "1393",
                "description": "전문 상담사와 24시간 무료 상담",
                "available": "24시간 무료"
            },
            ...
        ],
        "admin_notified": true,
        "recommendations": [
            "즉시 1393 또는 119에 전화하세요",
            ...
        ],
        "timestamp": "2025-11-05T14:30:00"
    }
    ```

    **Example Request (Level 0 Safe):**
    ```json
    {
        "crisis_level": 0,
        "user_id": "user456"
    }
    ```

    **Example Response:**
    ```json
    {
        "alert_type": "safe",
        "priority": "info",
        "message": "✅ **안전 상태**\\n\\n현재 위기 신호가 감지되지 않았습니다...",
        "actions_required": ["no_action"],
        "emergency_contacts": null,
        "admin_notified": false,
        "recommendations": [
            "현재 상태를 잘 유지하고 있습니다",
            ...
        ],
        "timestamp": "2025-11-05T14:31:00"
    }
    ```
    """
    try:
        alert_response = await alert_system.check_and_alert(
            crisis_level=request.crisis_level,
            user_id=request.user_id,
            message=request.message,
            crisis_indicators=request.crisis_indicators,
            user_age=request.user_age
        )

        return alert_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Alert generation failed: {str(e)}"
        )


@router.post("/alerts/quick")
async def quick_alert_check(
    request: QuickAlertRequest,
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Quick alert check with minimal information

    빠른 경고 확인 (간소화 버전)

    **Use Case:**
    - Fast crisis screening
    - Minimal information available
    - Quick response needed

    **Example:**
    ```
    POST /api/alerts/quick
    {
        "crisis_level": 3,
        "user_id": "user789"
    }
    ```

    **Response:**
    ```json
    {
        "alert_type": "high_risk",
        "priority": "high",
        "requires_immediate_action": true,
        "message": "높은 위기 수준 - 전문가 개입 권장",
        "primary_contact": "1393",
        "timestamp": "2025-11-05T14:35:00"
    }
    ```
    """
    try:
        alert_response = await alert_system.check_and_alert(
            crisis_level=request.crisis_level,
            user_id=request.user_id
        )

        # Simplified response
        return {
            "alert_type": alert_response.alert_type,
            "priority": alert_response.priority,
            "requires_immediate_action": alert_response.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH],
            "message": alert_response.message.split("\n")[0],  # First line only
            "primary_contact": "1393" if alert_response.crisis_level >= 2 else None,
            "full_response_available": True,
            "timestamp": alert_response.timestamp
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quick alert check failed: {str(e)}"
        )


@router.post("/alerts/emergency-contacts", response_model=List[EmergencyContact])
async def get_emergency_contacts(
    request: EmergencyContactsRequest,
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Get appropriate emergency contacts based on crisis level

    위기 수준별 긴급 연락처 조회

    **Returns contacts appropriate for crisis level:**
    - Level 4: All emergency services + professional contacts
    - Level 3: Emergency hotlines + professional referrals
    - Level 2: Primary support hotlines
    - Level 0-1: Reference contact (1393)

    **Age-specific contacts:**
    - Youth (<19): Includes 청소년 전화 (1388)
    - Adult (≥19): Standard contacts

    **Example Request:**
    ```json
    {
        "crisis_level": 4,
        "user_age": 16
    }
    ```

    **Example Response:**
    ```json
    [
        {
            "name": "청소년 전화 (청소년)",
            "phone": "1388",
            "description": "청소년 전용 상담 서비스",
            "available": "24시간"
        },
        {
            "name": "자살예방상담전화",
            "phone": "1393",
            "description": "전문 상담사와 24시간 무료 상담",
            "available": "24시간 무료"
        },
        {
            "name": "정신건강위기상담전화",
            "phone": "1577-0199",
            "description": "정신건강 위기 전문 상담",
            "available": "24시간"
        },
        {
            "name": "응급구조",
            "phone": "119",
            "description": "즉각적인 의료 지원이 필요한 경우",
            "available": "24시간"
        },
        ...
    ]
    ```
    """
    try:
        contacts = alert_system.get_emergency_contacts(
            crisis_level=request.crisis_level,
            user_age=request.user_age
        )

        return contacts

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve emergency contacts: {str(e)}"
        )


@router.get("/alerts/contacts/all")
async def get_all_emergency_contacts(
    alert_system: CrisisAlertSystem = Depends(get_alert_system)
):
    """
    Get all available emergency contacts

    모든 긴급 연락처 조회

    **Returns:**
    All emergency hotlines and professional contacts available in the system.

    **Categories:**
    - Emergency hotlines (24시간)
    - Professional referral contacts
    - Youth-specific services
    - Medical emergency services

    **Example Response:**
    ```json
    {
        "emergency_hotlines": [
            {
                "name": "자살예방상담전화",
                "phone": "1393",
                "description": "전문 상담사와 24시간 무료 상담",
                "available": "24시간 무료"
            },
            ...
        ],
        "professional_contacts": [
            {
                "name": "정신건강복지센터",
                "phone": "1577-0199",
                "description": "지역 정신건강복지센터 연결",
                "available": "평일 9:00-18:00"
            },
            ...
        ],
        "total_contacts": 7
    }
    ```
    """
    try:
        return {
            "emergency_hotlines": alert_system.EMERGENCY_CONTACTS,
            "professional_contacts": alert_system.PROFESSIONAL_CONTACTS,
            "total_contacts": len(alert_system.EMERGENCY_CONTACTS) + len(alert_system.PROFESSIONAL_CONTACTS),
            "categories": {
                "24_hour_emergency": ["1393", "1577-0199", "119", "1588-9191"],
                "youth_specific": ["1388"],
                "professional_referral": ["1577-0199", "02-2204-0114"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve contacts: {str(e)}"
        )


@router.get("/alerts/info/levels")
async def get_crisis_level_info():
    """
    Get information about all crisis levels

    위기 수준 정보 조회

    **Returns:**
    Detailed information about each crisis level (0-4) including:
    - Description
    - Alert type
    - Priority
    - Required actions
    - Response time
    - Admin notification

    **Example Response:**
    ```json
    {
        "levels": {
            "4": {
                "name": "긴급 (Imminent Danger)",
                "description": "즉각적인 위험 - 생명이 위험한 상황",
                "alert_type": "emergency",
                "priority": "critical",
                "actions": ["immediate_intervention"],
                "response_time": "즉시",
                "admin_notified": true,
                "emergency_contacts": ["1393", "1577-0199", "119"]
            },
            "3": {
                "name": "높음 (High Risk)",
                "description": "심각한 우려 - 전문가 개입 필요",
                "alert_type": "high_risk",
                "priority": "high",
                "actions": ["professional_referral"],
                "response_time": "수시간 이내",
                "admin_notified": true,
                "emergency_contacts": ["1393", "1577-0199"]
            },
            ...
        },
        "scale": "C-SSRS (Columbia Suicide Severity Rating Scale)"
    }
    ```
    """
    return {
        "levels": CRISIS_LEVELS_INFO,
        **CRISIS_SCALE_INFO
    }


@router.get("/alerts/capabilities")
async def get_alert_system_capabilities():
    """
    Get alert system capabilities and configuration

    경고 시스템 기능 및 설정 조회

    **Returns:**
    System capabilities, supported features, and configuration
    """
    return {
        "system": "Crisis Alert System",
        "version": "1.0.0",
        "capabilities": {
            "crisis_detection": {
                "scale": "C-SSRS (0-4)",
                "levels": 5,
                "real_time": True
            },
            "alert_generation": {
                "automatic": True,
                "customizable": True,
                "multi_language": ["Korean"],
                "age_specific": True
            },
            "emergency_contacts": {
                "total_contacts": 7,
                "24_hour_hotlines": 4,
                "youth_specific": True,
                "professional_referrals": True
            },
            "notifications": {
                "admin_alerts": True,
                "threshold": "Level 3+",
                "channels": ["console"],  # TODO: email, SMS, push
                "real_time": True
            },
            "response_times": {
                "level_4": "즉시",
                "level_3": "수시간 이내",
                "level_2": "24-48시간",
                "level_1": "정기 상담",
                "level_0": "해당 없음"
            }
        },
        "supported_features": [
            "Crisis level assessment (0-4)",
            "Age-specific recommendations",
            "Emergency contact provision",
            "Admin notifications (Level 3+)",
            "Alert history tracking",
            "Quick alert checks",
            "Comprehensive alert responses",
            "Korean language support"
        ],
        "integration": {
            "realtime_analysis": True,
            "crisis_detector": True,
            "dynamic_prompts": True,
            "cbt_stages": True
        }
    }
