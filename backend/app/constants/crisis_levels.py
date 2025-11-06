"""
Crisis Levels Constants
위기 수준 상수 정의

C-SSRS (Columbia Suicide Severity Rating Scale) 기반
"""

# Crisis levels information (0-4)
CRISIS_LEVELS_INFO = {
    "4": {
        "name": "긴급 (Imminent Danger)",
        "description": "즉각적인 위험 - 생명이 위험한 상황",
        "alert_type": "emergency",
        "priority": "critical",
        "actions": ["immediate_intervention"],
        "response_time": "즉시",
        "admin_notified": True,
        "emergency_contacts": ["1393", "1577-0199", "119", "1588-9191"],
        "key_indicators": [
            "구체적인 자살 계획",
            "자살 수단 접근",
            "즉각적인 위험 행동",
            "이별 메시지 작성"
        ]
    },
    "3": {
        "name": "높음 (High Risk)",
        "description": "심각한 우려 - 전문가 개입 필요",
        "alert_type": "high_risk",
        "priority": "high",
        "actions": ["professional_referral"],
        "response_time": "수시간 이내",
        "admin_notified": True,
        "emergency_contacts": ["1393", "1577-0199", "1588-9191"],
        "key_indicators": [
            "자살 생각과 의도",
            "계획 초기 단계",
            "지속적인 자해 생각",
            "높은 절망감"
        ]
    },
    "2": {
        "name": "중간 (Moderate Risk)",
        "description": "주의 필요 - 모니터링 강화",
        "alert_type": "moderate_risk",
        "priority": "medium",
        "actions": ["enhanced_monitoring"],
        "response_time": "24-48시간 내",
        "admin_notified": False,
        "emergency_contacts": ["1393", "1577-0199"],
        "key_indicators": [
            "자살 생각 (계획 없음)",
            "중간 정도의 고통",
            "일부 기능 저하",
            "지지 체계 약화"
        ]
    },
    "1": {
        "name": "낮음 (Low Risk)",
        "description": "경미한 우려 - 일반 지원",
        "alert_type": "low_risk",
        "priority": "low",
        "actions": ["standard_monitoring"],
        "response_time": "정기 상담 내",
        "admin_notified": False,
        "emergency_contacts": ["1393"],
        "key_indicators": [
            "일반적 스트레스",
            "경미한 우울감",
            "일상 유지 가능",
            "지지 체계 존재"
        ]
    },
    "0": {
        "name": "안전 (Safe)",
        "description": "위기 신호 없음",
        "alert_type": "safe",
        "priority": "info",
        "actions": ["no_action"],
        "response_time": "해당 없음",
        "admin_notified": False,
        "emergency_contacts": None,
        "key_indicators": [
            "안정적 상태",
            "적절한 대처",
            "지지 체계 양호",
            "기능 정상"
        ]
    }
}

# Crisis scale metadata
CRISIS_SCALE_INFO = {
    "scale": "C-SSRS (Columbia Suicide Severity Rating Scale)",
    "total_levels": 5,
    "critical_threshold": 3,
    "admin_notification_threshold": 3
}
