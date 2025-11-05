"""
Crisis Alert System
위기 경고 시스템

Provides crisis-level based alert management and notification system.

Author: AI Counselor System
Date: 2025-11-05
"""

from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from app.services.crisis_detector_enhanced import CSSRSLevel


class AlertType(str, Enum):
    """Alert type classification"""
    EMERGENCY = "emergency"  # Level 4 - Immediate danger
    HIGH_RISK = "high_risk"  # Level 3 - Serious concern
    MODERATE_RISK = "moderate_risk"  # Level 2 - Monitoring needed
    LOW_RISK = "low_risk"  # Level 1 - Minor concern
    SAFE = "safe"  # Level 0 - No concern


class AlertPriority(str, Enum):
    """Alert priority levels"""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Action required within hours
    MEDIUM = "medium"  # Enhanced monitoring
    LOW = "low"  # Standard monitoring
    INFO = "info"  # Informational only


class AlertAction(str, Enum):
    """Required actions for alerts"""
    IMMEDIATE_INTERVENTION = "immediate_intervention"
    PROFESSIONAL_REFERRAL = "professional_referral"
    ENHANCED_MONITORING = "enhanced_monitoring"
    STANDARD_MONITORING = "standard_monitoring"
    NO_ACTION = "no_action"


class EmergencyContact(BaseModel):
    """Emergency contact information"""
    name: str
    phone: str
    description: str
    available: str = "24시간"


class AlertResponse(BaseModel):
    """Alert response model"""
    alert_type: AlertType
    priority: AlertPriority
    message: str
    actions_required: List[AlertAction]
    emergency_contacts: Optional[List[EmergencyContact]] = None
    admin_notified: bool = False
    recommendations: List[str]
    timestamp: str


class CrisisAlertSystem:
    """
    Crisis Alert System
    위기 수준별 경고 및 대응 시스템

    Handles crisis-level based alerts with appropriate responses and notifications.
    """

    # Emergency hotlines
    EMERGENCY_CONTACTS = [
        EmergencyContact(
            name="자살예방상담전화",
            phone="1393",
            description="전문 상담사와 24시간 무료 상담",
            available="24시간 무료"
        ),
        EmergencyContact(
            name="정신건강위기상담전화",
            phone="1577-0199",
            description="정신건강 위기 전문 상담",
            available="24시간"
        ),
        EmergencyContact(
            name="응급구조",
            phone="119",
            description="즉각적인 의료 지원이 필요한 경우",
            available="24시간"
        ),
        EmergencyContact(
            name="한국생명의전화",
            phone="1588-9191",
            description="자살 위기 개입 및 상담",
            available="24시간"
        ),
        EmergencyContact(
            name="청소년 전화 (청소년)",
            phone="1388",
            description="청소년 전용 상담 서비스",
            available="24시간"
        )
    ]

    # Professional referral contacts
    PROFESSIONAL_CONTACTS = [
        EmergencyContact(
            name="정신건강복지센터",
            phone="1577-0199",
            description="지역 정신건강복지센터 연결",
            available="평일 9:00-18:00"
        ),
        EmergencyContact(
            name="국립정신건강센터",
            phone="02-2204-0114",
            description="전문 정신건강 서비스",
            available="평일 운영시간"
        )
    ]

    def __init__(self):
        """Initialize alert system"""
        pass

    async def check_and_alert(
        self,
        crisis_level: int,
        user_id: str,
        message: Optional[str] = None,
        crisis_indicators: Optional[List[str]] = None,
        user_age: Optional[int] = None
    ) -> AlertResponse:
        """
        Check crisis level and generate appropriate alert

        위기 수준 확인 및 적절한 경고 생성

        Args:
            crisis_level: C-SSRS crisis level (0-4)
            user_id: User identifier
            message: Optional user message that triggered alert
            crisis_indicators: List of detected crisis keywords
            user_age: User age for age-specific recommendations

        Returns:
            AlertResponse with appropriate actions and contacts
        """

        # Normalize crisis level
        crisis_level = max(0, min(4, crisis_level))

        # Route to appropriate handler
        if crisis_level >= 4:
            return await self._handle_emergency(user_id, crisis_indicators, user_age)
        elif crisis_level == 3:
            return await self._handle_high_risk(user_id, crisis_indicators, user_age)
        elif crisis_level == 2:
            return await self._handle_moderate_risk(user_id, crisis_indicators)
        elif crisis_level == 1:
            return await self._handle_low_risk(user_id)
        else:
            return await self._handle_safe(user_id)

    async def _handle_emergency(
        self,
        user_id: str,
        crisis_indicators: Optional[List[str]],
        user_age: Optional[int]
    ) -> AlertResponse:
        """
        Handle Level 4: Emergency / Imminent Danger

        즉각적인 위험 - 긴급 개입 필요
        """

        # Build emergency message
        message = """
⚠️ **긴급 상황 감지**

지금 즉시 전문적인 도움이 필요합니다.

**즉시 연락할 수 있는 곳:**

📞 **자살예방상담전화: 1393** (24시간 무료)
   → 지금 바로 전문 상담사와 연결됩니다

📞 **정신건강위기상담전화: 1577-0199** (24시간)
   → 정신건강 위기 전문 상담

📞 **응급구조: 119**
   → 즉각적인 의료 지원이 필요한 경우

📞 **한국생명의전화: 1588-9191** (24시간)
   → 자살 위기 개입 및 상담
"""

        # Add youth-specific contact if applicable
        if user_age and user_age < 19:
            message += """
📞 **청소년 전화: 1388** (24시간)
   → 청소년 전용 상담 서비스
"""

        message += """

**당신은 혼자가 아닙니다.**
지금 이 순간, 당신의 고통을 이해하고 도울 준비가 된 전문가들이 대기하고 있습니다.

**지금 전화를 걸어주세요.** 그것이 당신이 지금 할 수 있는 가장 용감한 선택입니다.
"""

        # Prepare emergency contacts list
        emergency_contacts = self.EMERGENCY_CONTACTS.copy()

        # Filter for age-appropriate contacts
        if user_age and user_age < 19:
            # Ensure youth contact is prominently listed
            emergency_contacts = [c for c in emergency_contacts if c.name == "청소년 전화 (청소년)"] + \
                               [c for c in emergency_contacts if c.name != "청소년 전화 (청소년)"]

        # Recommendations
        recommendations = [
            "즉시 1393 또는 119에 전화하세요",
            "가능하다면 신뢰할 수 있는 사람에게 지금 당신의 위치와 상태를 알리세요",
            "위험한 물건이나 약물로부터 멀리 떨어지세요",
            "안전한 장소로 이동하세요",
            "혼자 있지 마세요 - 가족, 친구, 또는 이웃에게 연락하세요"
        ]

        if crisis_indicators:
            recommendations.append(f"감지된 위기 신호: {', '.join(crisis_indicators[:3])}")

        # Notify admin (this would integrate with notification service)
        await self._notify_admin(
            user_id=user_id,
            alert_type=AlertType.EMERGENCY,
            priority=AlertPriority.CRITICAL,
            message=f"User {user_id} - Level 4 emergency detected"
        )

        return AlertResponse(
            alert_type=AlertType.EMERGENCY,
            priority=AlertPriority.CRITICAL,
            message=message,
            actions_required=[AlertAction.IMMEDIATE_INTERVENTION],
            emergency_contacts=emergency_contacts,
            admin_notified=True,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    async def _handle_high_risk(
        self,
        user_id: str,
        crisis_indicators: Optional[List[str]],
        user_age: Optional[int]
    ) -> AlertResponse:
        """
        Handle Level 3: High Risk

        높은 위험 - 전문가 개입 권장
        """

        message = """
⚠️ **높은 위기 수준 감지**

현재 상태가 매우 우려됩니다. 전문가의 도움을 받으시길 강력히 권장합니다.

**전문가 상담 연결:**

📞 **자살예방상담전화: 1393** (24시간 무료)
   → 전문 상담사와 즉시 상담 가능

📞 **정신건강위기상담전화: 1577-0199**
   → 정신건강 전문가 상담

📞 **한국생명의전화: 1588-9191**
   → 위기 상담 및 지원
"""

        if user_age and user_age < 19:
            message += """
📞 **청소년 전화: 1388**
   → 청소년 전문 상담
"""

        message += """

**전문적 지원 이용을 고려하세요:**
- 정신건강복지센터 (1577-0199)
- 가까운 병원 정신건강의학과
- 학교 상담센터 (학생의 경우)

**당신의 안전이 가장 중요합니다.**
혼자 견디려 하지 마시고, 전문가의 도움을 받으세요.
"""

        # Professional contacts
        professional_contacts = self.EMERGENCY_CONTACTS[:4]  # Main emergency contacts
        if user_age and user_age < 19:
            professional_contacts.append(self.EMERGENCY_CONTACTS[4])  # Youth hotline

        professional_contacts.extend(self.PROFESSIONAL_CONTACTS)

        recommendations = [
            "가능한 빨리 전문 상담사와 상담하세요 (1393)",
            "정신건강복지센터를 방문하거나 연락하세요",
            "신뢰할 수 있는 사람에게 당신의 상태를 알리세요",
            "혼자 있는 시간을 최소화하세요",
            "정기적으로 안전을 확인받을 수 있는 체계를 만드세요"
        ]

        if crisis_indicators:
            recommendations.append(f"주의 필요 신호: {', '.join(crisis_indicators[:3])}")

        # Notify admin
        await self._notify_admin(
            user_id=user_id,
            alert_type=AlertType.HIGH_RISK,
            priority=AlertPriority.HIGH,
            message=f"User {user_id} - Level 3 high risk detected"
        )

        return AlertResponse(
            alert_type=AlertType.HIGH_RISK,
            priority=AlertPriority.HIGH,
            message=message,
            actions_required=[AlertAction.PROFESSIONAL_REFERRAL],
            emergency_contacts=professional_contacts,
            admin_notified=True,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    async def _handle_moderate_risk(
        self,
        user_id: str,
        crisis_indicators: Optional[List[str]]
    ) -> AlertResponse:
        """
        Handle Level 2: Moderate Risk

        중간 위험 - 주의 깊은 모니터링
        """

        message = """
⚠️ **중간 수준의 위기 신호 감지**

현재 상태가 우려되는 부분이 있습니다. 주의 깊은 관찰이 필요합니다.

**권장 사항:**

1️⃣ **전문 상담 고려**
   - 자살예방상담전화: 1393 (24시간)
   - 정신건강위기상담전화: 1577-0199
   - 편안한 시간에 전화하셔도 됩니다

2️⃣ **지지 체계 활용**
   - 신뢰할 수 있는 친구나 가족과 대화
   - 학교/직장 상담실 이용
   - 지역 상담센터 방문 고려

3️⃣ **자기 관찰**
   - 증상이 악화되는지 주의깊게 관찰
   - 기분, 생각, 행동의 변화 기록
   - 도움이 필요하다고 느껴지면 즉시 연락

**당신의 고통이 유효하며, 도움을 구하는 것은 강함의 표시입니다.**
"""

        recommendations = [
            "증상 변화를 주의 깊게 모니터링하세요",
            "신뢰할 수 있는 사람과 정기적으로 연락하세요",
            "전문 상담을 고려하세요 (1393)",
            "자기돌봄 활동을 유지하세요 (수면, 식사, 운동)",
            "고립되지 않도록 사회적 연결을 유지하세요"
        ]

        if crisis_indicators:
            recommendations.append(f"관찰 중인 신호: {', '.join(crisis_indicators[:3])}")

        # Limited emergency contacts for reference
        support_contacts = [
            self.EMERGENCY_CONTACTS[0],  # 1393
            self.EMERGENCY_CONTACTS[1],  # 1577-0199
        ]

        return AlertResponse(
            alert_type=AlertType.MODERATE_RISK,
            priority=AlertPriority.MEDIUM,
            message=message,
            actions_required=[AlertAction.ENHANCED_MONITORING],
            emergency_contacts=support_contacts,
            admin_notified=False,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    async def _handle_low_risk(
        self,
        user_id: str
    ) -> AlertResponse:
        """
        Handle Level 1: Low Risk

        낮은 위험 - 일반 지원
        """

        message = """
ℹ️ **경미한 스트레스 신호 감지**

현재 약간의 어려움이 감지되었지만, 일반적인 수준입니다.

**제안:**

💚 **자기돌봄**
   - 충분한 수면 (7-9시간)
   - 규칙적인 식사
   - 가벼운 운동이나 산책

💬 **대화**
   - 신뢰하는 사람과 이야기 나누기
   - 감정을 표현하는 것이 도움이 됩니다

📞 **필요시 언제든지**
   - 자살예방상담전화: 1393
   - 정신건강위기상담전화: 1577-0199

**작은 어려움도 중요합니다. 필요하면 언제든 도움을 요청하세요.**
"""

        recommendations = [
            "자기돌봄 활동을 유지하세요",
            "스트레스 관리 기법을 실천하세요",
            "필요시 전문 상담을 고려하세요",
            "긍정적인 사회적 관계를 유지하세요"
        ]

        support_contacts = [
            self.EMERGENCY_CONTACTS[0],  # 1393 for reference
        ]

        return AlertResponse(
            alert_type=AlertType.LOW_RISK,
            priority=AlertPriority.LOW,
            message=message,
            actions_required=[AlertAction.STANDARD_MONITORING],
            emergency_contacts=support_contacts,
            admin_notified=False,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    async def _handle_safe(
        self,
        user_id: str
    ) -> AlertResponse:
        """
        Handle Level 0: Safe

        안전 - 위기 신호 없음
        """

        message = """
✅ **안전 상태**

현재 위기 신호가 감지되지 않았습니다.

**지속적인 웰빙을 위해:**

🌱 건강한 일상 유지
💬 열린 대화 지속
📚 자기 성찰 계속

언제든지 이야기 나눌 준비가 되어 있습니다.
"""

        recommendations = [
            "현재 상태를 잘 유지하고 있습니다",
            "정기적인 자기돌봄을 계속하세요",
            "필요하면 언제든 대화할 수 있습니다"
        ]

        return AlertResponse(
            alert_type=AlertType.SAFE,
            priority=AlertPriority.INFO,
            message=message,
            actions_required=[AlertAction.NO_ACTION],
            emergency_contacts=None,
            admin_notified=False,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    async def _notify_admin(
        self,
        user_id: str,
        alert_type: AlertType,
        priority: AlertPriority,
        message: str
    ) -> bool:
        """
        Notify system administrators of critical alerts

        시스템 관리자에게 중요 경고 알림

        In production, this would integrate with:
        - Email notification service
        - SMS/push notification service
        - Admin dashboard alerts
        - Logging/monitoring system

        Args:
            user_id: User identifier
            alert_type: Type of alert
            priority: Alert priority
            message: Alert message

        Returns:
            True if notification sent successfully
        """

        # Log the alert
        print(f"🚨 ADMIN ALERT - {priority.value.upper()}")
        print(f"   User: {user_id}")
        print(f"   Type: {alert_type.value}")
        print(f"   Time: {datetime.now().isoformat()}")
        print(f"   Message: {message}")
        print("-" * 60)

        # In production, implement actual notification logic:
        # - Send email to admin team
        # - Send SMS for critical alerts
        # - Update admin dashboard
        # - Log to monitoring system (e.g., Sentry, DataDog)
        # - Create incident ticket if needed

        # TODO: Integrate with notification service
        # await notification_service.send_admin_alert(...)

        return True

    def get_emergency_contacts(
        self,
        crisis_level: int,
        user_age: Optional[int] = None
    ) -> List[EmergencyContact]:
        """
        Get appropriate emergency contacts based on crisis level and age

        Args:
            crisis_level: C-SSRS crisis level (0-4)
            user_age: User age for age-specific contacts

        Returns:
            List of relevant emergency contacts
        """

        if crisis_level >= 4:
            contacts = self.EMERGENCY_CONTACTS.copy()
        elif crisis_level >= 3:
            contacts = self.EMERGENCY_CONTACTS[:4] + self.PROFESSIONAL_CONTACTS
        elif crisis_level >= 2:
            contacts = self.EMERGENCY_CONTACTS[:2]
        else:
            contacts = [self.EMERGENCY_CONTACTS[0]]  # Just 1393 for reference

        # Add youth-specific contact if applicable
        if user_age and user_age < 19 and crisis_level >= 3:
            youth_contact = self.EMERGENCY_CONTACTS[4]
            if youth_contact not in contacts:
                contacts.insert(1, youth_contact)

        return contacts

    async def get_alert_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get alert history for a user

        In production, this would query a database of alert records.

        Args:
            user_id: User identifier
            limit: Maximum number of alerts to return

        Returns:
            List of alert records
        """

        # TODO: Implement database query for alert history
        # This would track:
        # - Alert timestamps
        # - Crisis levels over time
        # - Actions taken
        # - Response effectiveness

        return []
